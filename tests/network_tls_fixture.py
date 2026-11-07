"""Test image entrypoint: controlled TLS endpoint alongside production proxy."""
import asyncio
import http.server
import ssl
import socket
import sys
import threading
import base64
import hashlib
import time
import json

sys.path.insert(0, '/opt/claude-egress')
import proxy

# A deterministic test resolver supplies only the policy's explicit loopback
# exception. Production proxy resolution/address validation still runs in full.
original_resolver = socket.getaddrinfo
def fixture_resolver(host, port, *args, **kwargs):
    return original_resolver('127.0.0.1' if host == 'localhost.localdomain' else host,
                             port, *args, **kwargs)
socket.getaddrinfo = fixture_resolver


class Endpoint(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', 'https://unapproved.test/?token=fixture-secret-token')
            self.end_headers()
            return
        if self.path == '/websocket':
            self.send_response(101)
            self.send_header('Upgrade', 'websocket')
            self.send_header('Connection', 'Upgrade')
            key = self.headers['Sec-WebSocket-Key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
            self.send_header('Sec-WebSocket-Accept', base64.b64encode(hashlib.sha1(key.encode()).digest()).decode())
            self.end_headers()
            self.wfile.write(b'\x81\x02ok')
            return
        if self.path == '/large':
            body = b'large-frame-boundary-' * 65536
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == '/long-stream':
            self.send_response(200)
            self.send_header('Content-Length', str(75 * len(b'progress\n')))
            self.end_headers()
            for _ in range(75):
                self.wfile.write(b'progress\n')
                self.wfile.flush()
                time.sleep(.2)
            return
        if self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-Length', '3')
            self.end_headers()
            for part in (b'a', b'b', b'c'):
                self.wfile.write(part)
                self.wfile.flush()
                time.sleep(0.2)
            return
        body = b'controlled-production-proxy-ok'
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # Synthetic Messages API only: no real model or credentials are used.
        size = int(self.headers.get('Content-Length', '0'))
        if not 0 < size <= 8 * 1024 * 1024:
            self.send_error(400)
            return
        request = json.loads(self.rfile.read(size))
        if self.path.startswith('/v1/messages/count_tokens'):
            body = b'{"input_tokens":1}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if not self.path.startswith('/v1/messages'):
            self.send_error(404)
            return
        results = [part for message in request.get('messages', [])
                   for part in message.get('content', []) if isinstance(part, dict)
                   and part.get('type') == 'tool_result' and part.get('tool_use_id') == 'toolu_fixture_bash']
        tool_available = any(tool.get('name') == 'Bash' for tool in request.get('tools', []))
        use_tool = tool_available and not results
        if use_tool:
            block = {'type': 'tool_use', 'id': 'toolu_fixture_bash', 'name': 'Bash', 'input': {}}
            command = "python3 -c \"import socket,errno;\ntry: socket.socket(socket.AF_UNIX)\nexcept OSError as e: assert e.errno==errno.EPERM\nelse: raise AssertionError('tool escaped')\" && printf actual-claude-tool-ok > claude-tool-sentinel"
            delta = {'type': 'input_json_delta', 'partial_json': json.dumps({
                'command': command, 'description': 'Run the credential-free confined tool fixture'})}
            reason = 'tool_use'
        else:
            block = {'type': 'text', 'text': ''}
            text = 'fixture-tool-complete' if results and not any(r.get('is_error') for r in results) else 'fixture-tool-error'
            delta = {'type': 'text_delta', 'text': text}
            reason = 'end_turn'
        message = {'id': 'msg_fixture', 'type': 'message', 'role': 'assistant',
                   'content': [], 'model': request.get('model', 'fixture'),
                   'stop_reason': None, 'stop_sequence': None,
                   'usage': {'input_tokens': 1, 'output_tokens': 0}}
        events = [('message_start', {'message': message}),
                  ('content_block_start', {'index': 0, 'content_block': block}),
                  ('content_block_delta', {'index': 0, 'delta': delta}),
                  ('content_block_stop', {'index': 0}),
                  ('message_delta', {'delta': {'stop_reason': reason, 'stop_sequence': None}, 'usage': {'output_tokens': 1}}),
                  ('message_stop', {})]
        body = b''.join(('event: ' + event + '\ndata: ' + json.dumps({'type': event, **data}) + '\n\n').encode() for event, data in events)
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('request-id', 'synthetic-request')
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def log_message(self, *args):
        pass


server = http.server.ThreadingHTTPServer(('127.0.0.1', 8443), Endpoint)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('/test/cert.pem', '/test/key.pem')
server.socket = context.wrap_socket(server.socket, server_side=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
asyncio.run(proxy.main())
