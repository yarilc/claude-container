FROM docker.io/library/node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    CLAUDE_CONFIG_DIR=/claude-home/.claude \
    HOME=/claude-home

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
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
    && npm install --global --omit=dev @anthropic-ai/claude-code \
    && npm install -g @fission-ai/openspec@latest \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.npm \
    && mkdir -p /claude-home \
    && chmod 1777 /claude-home

WORKDIR /workspace
ENTRYPOINT ["claude"]
