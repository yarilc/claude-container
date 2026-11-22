# Claude agent part for the shared launcher core (launcher/core.sh). It mirrors
# agent/profile.json and agent/policies/default.json; tests/test_alignment.py
# compares them. See docs/launcher-contract.md in sandbox-container.
# The core sources this file: it reads the AGENT_* data and hook outputs and
# defines the core state the hooks read.
# shellcheck shell=bash disable=SC2034,SC2154
AGENT_NAME=claude-container
AGENT_DISPLAY_NAME=Claude
AGENT_WRAPPER=claude-container.sh
AGENT_ENV_PREFIX=CLAUDE_CONTAINER
AGENT_LABEL_NAMESPACE=io.claude-container
AGENT_IMAGE=localhost/claude-code
AGENT_PROXY_IMAGE=localhost/claude-egress
AGENT_HOME=/claude-home
AGENT_COMMAND=claude
AGENT_EXEC=/usr/local/bin/claude
AGENT_CONFIG_DIR_ENV=CLAUDE_CONFIG_DIR
AGENT_CONFIG_HOME=.claude
AGENT_SHARED_DIRS=(.config/openspec)
AGENT_PRIVATE_SHARED_DIRS=0
AGENT_APPROVAL_BYPASS_ENV=CLAUDE_YOLO
AGENT_EXEC_TMP=0
AGENT_INSTALL_FILES=()
AGENT_CREDENTIALS=(anthropic-api=ANTHROPIC_API_KEY anthropic-account=)
AGENT_POLICY_HOSTS=("anthropic-api=api.anthropic.com" "anthropic-account=api.anthropic.com platform.claude.com")
AGENT_SESSION_ENV=()
AGENT_RESTRICTED_ENV=()
# Optional traffic is disabled in provider sessions, where it would be denied.
AGENT_PROVIDER_ENV=(CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_AUTOUPDATER=1 DISABLE_TELEMETRY=1
    DISABLE_ERROR_REPORTING=1 ENABLE_CLAUDEAI_MCP_SERVERS=false CLAUDE_CODE_DISABLE_ARTIFACT=1)
AGENT_UNSET_ENV=()
AGENT_RESERVED_ENV=()

agent_help() {
    printf '  CLAUDE_YOLO             enable --dangerously-skip-permissions: 1, true or yes\n'
    printf '                          (default: disabled; never applied in shell mode)\n'
}

# CLAUDE_YOLO: Claude's own approval bypass; the core skips it in shell mode.
agent_approval_bypass() {
    agent_bypass_args=(--dangerously-skip-permissions)
}
