# Image inputs are pinned. Update them only through the documented maintenance
# procedure (docs/validation.md): CLAUDE_CODE_VERSION must equal the CLI version
# recorded in agent/policies/default.json `tested.cli`.
FROM docker.io/library/node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da

ARG CLAUDE_CODE_VERSION=2.1.316
ARG OPENSPEC_VERSION=1.16.0

ENV DEBIAN_FRONTEND=noninteractive \
    CLAUDE_CONFIG_DIR=/claude-home/.claude \
    EDITOR=nano \
    VISUAL=nano \
    HOME=/claude-home \
    DISABLE_AUTOUPDATER=1

# Debian packages are fetched only over verified HTTPS, so builds need no outbound
# port 80. The slim base has no ca-certificates, so the pinned base's Node.js root
# certificates verify the fetches until Debian ca-certificates is installed. With
# host CA trust enabled, the selected bundle arrives as the optional build-ca
# secret (never stored in a layer) and is appended for TLS-intercepting networks.
# The temporary bundle stays readable by apt's _apt user and is removed in this step.
RUN --mount=type=secret,id=build-ca,required=false \
    node -e 'process.stdout.write(require("tls").rootCertificates.join("\n") + "\n")' \
        > /tmp/apt-bootstrap-ca.pem \
    && if [ -s /run/secrets/build-ca ]; then cat /run/secrets/build-ca >> /tmp/apt-bootstrap-ca.pem; fi \
    && sed -i 's|^URIs: http://|URIs: https://|' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::https::CAInfo=/tmp/apt-bootstrap-ca.pem update \
    && apt-get -o Acquire::https::CAInfo=/tmp/apt-bootstrap-ca.pem install --no-install-recommends -y \
        bash \
        bzip2 \
        bubblewrap \
        ca-certificates \
        coreutils \
        curl \
        diffutils \
        file \
        findutils \
        gawk \
        git \
        grep \
        jq \
        less \
        nano \
        patch \
        podman \
        procps \
        python3 \
        ripgrep \
        sed \
        tar \
        unzip \
        util-linux \
        xz-utils \
        zip \
    && rm -f /tmp/apt-bootstrap-ca.pem \
    && npm install --global --omit=dev "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
        "@fission-ai/openspec@${OPENSPEC_VERSION}" \
    && echo 'unset historylog' >> /etc/nanorc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.npm \
    && mkdir -p /claude-home \
    && chmod 1777 /claude-home

WORKDIR /workspace
COPY network/relay.py network/mux.py /opt/sandbox-egress/
ENTRYPOINT ["claude"]
