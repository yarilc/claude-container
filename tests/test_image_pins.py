"""Credential-free checks that the runtime image inputs are pinned (B05)."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ('@anthropic-ai/claude-code', '@fission-ai/openspec')
VERSION = re.compile(r'\d+\.\d+\.\d+')


def pins(recipe):
    """Return (base reference, {ARG name: default}, installed package specifiers)."""
    lines = recipe.replace('\\\n', ' ').splitlines()
    bases = [line.split()[1] for line in lines if line.startswith('FROM ')]
    if len(bases) != 1:
        raise ValueError('expected exactly one FROM line')
    args = dict(re.findall(r'^ARG ([A-Z_]+)=(\S+)$', recipe, re.MULTILINE))
    installs = []
    for line in lines:
        if 'npm install' in line or 'npm i ' in line:
            for command in line.split('&&'):
                if 'npm install' not in command and 'npm i ' not in command:
                    continue
                for token in command.split():
                    token = token.strip('"\'')
                    if token.startswith('@') or (not token.startswith('-') and '/' not in token
                                                 and token not in ('npm', 'install', 'i')):
                        for name, value in args.items():
                            token = token.replace('${' + name + '}', value).replace('$' + name, value)
                        installs.append(token)
    return bases[0], args, installs


def violations(recipe, tested_cli):
    found = []
    base, args, installs = pins(recipe)
    if not re.fullmatch(r'[a-z0-9./:-]+@sha256:[a-f0-9]{64}', base):
        found.append('base image is not pinned by digest: ' + base)
    seen = {}
    for spec in installs:
        name, _, version = spec.rpartition('@')
        if not name:
            found.append('unpinned package: ' + spec)
            continue
        if not VERSION.fullmatch(version):
            found.append('package is not pinned to an exact version: ' + spec)
        seen[name] = version
    for package in PACKAGES:
        if package not in seen:
            found.append('required package is not installed with a pinned version: ' + package)
    tested = re.match(r'(\d+\.\d+\.\d+)\b', tested_cli)
    cli = seen.get(PACKAGES[0], '')
    if not tested or tested[1] != cli:
        found.append(f'pinned CLI {cli or "(none)"} differs from policy tested.cli {tested_cli!r}')
    return found


SOURCES = '/etc/apt/sources.list.d/debian.sources'
BOOTSTRAP_CA = '/tmp/apt-bootstrap-ca.pem'
INSECURE_APT = re.compile(r'Verify-(?:Peer|Host)\s*[= ]\s*"?(?:false|no|0)\b'
                          r'|AllowInsecureRepositories|--allow-insecure|--allow-unauthenticated'
                          r'|trusted=yes|\[trusted', re.IGNORECASE)


def transport_violations(recipe):
    """Return package-source transport violations (Debian over verified HTTPS only)."""
    text = recipe.replace('\\\n', ' ')
    found = []
    if re.search(r'http://deb\.debian\.org', text):
        found.append('plain-HTTP Debian source: http://deb.debian.org')
    for match in INSECURE_APT.finditer(text):
        found.append('apt TLS or signature verification disabled: ' + match[0])
    rewrite = re.search(r"sed -i '?s\|\^URIs: http://\|URIs: https://\|'? " + re.escape(SOURCES), text)
    update = re.search(r'apt-get\b[^&]*\bupdate\b', text)
    if not rewrite:
        found.append('Debian sources are not rewritten to HTTPS')
    elif update and update.start() < rewrite.start():
        found.append('Debian sources are rewritten to HTTPS only after apt-get update')
    # Bootstrap trust comes only from the pinned base's Node roots and is removed in the same step.
    bootstrap = re.search(r'rootCertificates[^&]*>\s*' + re.escape(BOOTSTRAP_CA), text)
    if not bootstrap or (rewrite and bootstrap.start() > rewrite.start()):
        found.append('bootstrap CA bundle is not exported from the base Node roots before the rewrite')
    for command in re.findall(r'apt-get\b[^&]*', text):
        if re.search(r'\b(update|install)\b', command) and 'Acquire::https::CAInfo=' + BOOTSTRAP_CA not in command:
            found.append('apt-get fetch without the bootstrap CA: ' + command.split(' -y')[0].strip())
    # The optional host CA arrives only as a build secret, never as a copied file.
    if not re.search(r'RUN --mount=type=secret,id=build-ca,required=false\b', text):
        found.append('optional build-ca secret mount is missing')
    for match in re.finditer(r'(?im)^(?:COPY|ADD)\b[^\n]*(?:\.pem|\.crt|ca-?bundle|certs?\b)', text):
        found.append('CA material copied into the image: ' + match[0])
    if 'build-ca' in text and not re.search(r'cat /run/secrets/build-ca >> ' + re.escape(BOOTSTRAP_CA), text):
        found.append('build-ca secret is not appended to the bootstrap CA bundle')
    steps = [line for line in text.splitlines() if BOOTSTRAP_CA in line]
    if not steps or len(steps) != 1 or 'rm -f ' + BOOTSTRAP_CA not in steps[0]:
        found.append('bootstrap CA bundle is not removed in the step that creates it')
    return found


class ImagePinTests(unittest.TestCase):
    def setUp(self):
        self.recipe = (ROOT / 'Containerfile').read_text()
        self.tested_cli = json.loads((ROOT / 'agent/policies/default.json').read_text())['tested']['cli']

    def test_shipped_recipe_is_pinned_and_matches_policy(self):
        self.assertEqual(violations(self.recipe, self.tested_cli), [])
        _, args, _ = pins(self.recipe)
        self.assertEqual(args['CLAUDE_CODE_VERSION'], self.tested_cli.split()[0])
        self.assertRegex(self.recipe, r'(?m)^\s+DISABLE_AUTOUPDATER=1$')

    def test_mutated_recipes_are_rejected(self):
        digest = re.search(r'@sha256:[a-f0-9]{64}', self.recipe)
        cases = {
            'tag-only base': self.recipe.replace(digest[0], '') if digest else self.recipe,
            'latest package': self.recipe.replace('"@fission-ai/openspec@${OPENSPEC_VERSION}"',
                                                  '@fission-ai/openspec@latest'),
            'unversioned package': self.recipe.replace('"@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"',
                                                       '@anthropic-ai/claude-code'),
            'version range': self.recipe.replace('ARG OPENSPEC_VERSION=1.16.0', 'ARG OPENSPEC_VERSION=^1.16.0'),
            'diverging cli': self.recipe.replace('ARG CLAUDE_CODE_VERSION=2.1.316', 'ARG CLAUDE_CODE_VERSION=2.1.317'),
        }
        for name, recipe in cases.items():
            with self.subTest(name=name):
                self.assertNotEqual(recipe, self.recipe)
                self.assertTrue(violations(recipe, self.tested_cli))
        message = violations(cases['diverging cli'], self.tested_cli)
        self.assertTrue(any('2.1.317' in item and '2.1.316' in item for item in message), message)


    def test_package_sources_use_verified_https(self):
        self.assertEqual(transport_violations(self.recipe), [])

    def test_insecure_transport_recipes_are_rejected(self):
        rewrite = "sed -i 's|^URIs: http://|URIs: https://|' " + SOURCES
        option = '-o Acquire::https::CAInfo=' + BOOTSTRAP_CA
        cases = {
            'plain http restored': self.recipe.replace(rewrite, 'true'),
            'peer verification disabled': self.recipe.replace(option, option + ' -o Acquire::https::Verify-Peer=false', 1),
            'host verification disabled': self.recipe.replace(option, option + ' -o Acquire::https::Verify-Host=false', 1),
            'insecure repositories': self.recipe.replace(option, option + ' -o Acquire::AllowInsecureRepositories=true', 1),
            'rewrite after update': self.recipe.replace('    && ' + rewrite + ' \\\n', '').replace(
                '    && npm install', '    && ' + rewrite + ' \\\n    && npm install', 1),
            'literal http source': self.recipe.replace(rewrite, rewrite + ' && echo http://deb.debian.org/debian'),
            'fetch without bootstrap ca': self.recipe.replace(option + ' update', 'update', 1),
            'bootstrap ca kept': self.recipe.replace('    && rm -f ' + BOOTSTRAP_CA + ' \\\n', ''),
            'secret mount required': self.recipe.replace('id=build-ca,required=false', 'id=build-ca,required=true'),
            'secret not appended': self.recipe.replace('cat /run/secrets/build-ca >> ', 'true ', 1),
            'bundle copied': self.recipe.replace('WORKDIR /workspace', 'COPY bundle.pem /etc/ssl/certs/host.pem\nWORKDIR /workspace'),
        }
        for name, recipe in cases.items():
            with self.subTest(name=name):
                self.assertNotEqual(recipe, self.recipe)
                self.assertTrue(transport_violations(recipe))


TOOLCHAIN_CA = '/tmp/apk-bootstrap-ca.pem'


def toolchain_violations(recipe):
    """The guard toolchain keeps exact pins and takes the host CA only as an optional build secret."""
    text = recipe.replace('\\\n', ' ')
    found = []
    if not re.search(r'(?m)^FROM docker\.io/library/alpine@sha256:[a-f0-9]{64}$', recipe):
        found.append('toolchain base is not pinned by digest')
    for package in re.findall(r'apk add --no-cache ([^&\n]+)', text):
        for spec in package.split():
            if not re.fullmatch(r'[a-z0-9-]+=[0-9][A-Za-z0-9._-]*', spec):
                found.append('toolchain package is not pinned: ' + spec)
    if not re.search(r'RUN --mount=type=secret,id=build-ca,required=false\b', text):
        found.append('optional build-ca secret mount is missing')
    if not re.search(r'SSL_CERT_FILE=' + re.escape(TOOLCHAIN_CA) + r' apk add\b', text):
        found.append('apk does not verify against the bootstrap bundle')
    if 'rm -f ' + TOOLCHAIN_CA not in text or len([l for l in text.splitlines() if TOOLCHAIN_CA in l]) != 1:
        found.append('toolchain bootstrap bundle is not removed in the step that creates it')
    if INSECURE_APT.search(text) or re.search(r'--allow-untrusted|--no-check-certificate|http://', text):
        found.append('toolchain fetch verification weakened')
    if re.search(r'(?im)^(?:COPY|ADD)\b', recipe):
        found.append('toolchain recipe copies host files')
    return found


class ToolchainRecipeTests(unittest.TestCase):
    def test_toolchain_recipe_is_pinned_and_takes_ca_only_as_secret(self):
        recipe = (ROOT / 'network/guard-build.Containerfile').read_text()
        self.assertEqual(toolchain_violations(recipe), [])
        cases = {
            'unpinned package': recipe.replace('gcc=13.2.1_git20240309-r1', 'gcc'),
            'required secret': recipe.replace('required=false', 'required=true'),
            'bundle kept': recipe.replace('    && rm -f ' + TOOLCHAIN_CA, '    && true'),
            'no bootstrap trust': recipe.replace('SSL_CERT_FILE=' + TOOLCHAIN_CA + ' ', ''),
            'untrusted packages': recipe.replace('apk add --no-cache', 'apk add --allow-untrusted --no-cache'),
            'copied bundle': recipe.replace('ENV LC_ALL', 'COPY bundle.pem /etc/ssl/certs/host.pem\nENV LC_ALL'),
        }
        for name, mutated in cases.items():
            with self.subTest(name=name):
                self.assertNotEqual(mutated, recipe)
                self.assertTrue(toolchain_violations(mutated))
        ignore = (ROOT / 'network/.containerignore').read_text().splitlines()
        self.assertIn('!podman-build-secret*', ignore)


if __name__ == '__main__':
    unittest.main()
