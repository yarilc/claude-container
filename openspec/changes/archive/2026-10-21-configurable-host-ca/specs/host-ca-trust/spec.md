# Spec Delta

## Purpose

Controls whether the Claude Container wrapper exposes a host CA certificate bundle to tools running inside the container, and which bundle is used.

## ADDED Requirements

### Requirement: Host CA trust is disabled by default
The wrapper SHALL NOT mount any host certificate bundle and SHALL NOT set CA bundle environment variables unless host CA trust is enabled.

#### Scenario: Variable not set
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_TRUST_HOST_CA` unset
- **THEN** the container has no host certificate mount and no `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE` or `NODE_EXTRA_CA_CERTS` variables set by the wrapper

#### Scenario: Variable disabled explicitly
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_TRUST_HOST_CA` set to `0`, `false` or `no`
- **THEN** the behavior is the same as when the variable is unset

### Requirement: Host CA trust is enabled by an explicit flag
The wrapper SHALL enable host CA trust when `CLAUDE_CONTAINER_TRUST_HOST_CA` is set to `1`, `true` or `yes`, case-insensitively. Any other non-empty value SHALL cause the wrapper to fail before starting the container, with an error message that names the variable and the accepted values.

#### Scenario: Variable enabled
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_TRUST_HOST_CA` set to `1`
- **THEN** host CA trust is enabled

#### Scenario: Invalid value
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_TRUST_HOST_CA` set to `maybe`
- **THEN** the wrapper exits with a non-zero status and prints an error naming `CLAUDE_CONTAINER_TRUST_HOST_CA` and the accepted values, and no container is started

### Requirement: Bundle selection
When host CA trust is enabled, the wrapper SHALL use the file named by `CLAUDE_CONTAINER_CA_BUNDLE` if that variable is set. If it is not set, the wrapper SHALL use the first existing file among `/etc/ssl/certs/ca-certificates.crt` and `/etc/pki/tls/certs/ca-bundle.crt`.

#### Scenario: Explicit bundle path
- **WHEN** host CA trust is enabled and `CLAUDE_CONTAINER_CA_BUNDLE` names an existing file
- **THEN** that file is the bundle exposed to the container

#### Scenario: Default bundle path
- **WHEN** host CA trust is enabled, `CLAUDE_CONTAINER_CA_BUNDLE` is unset, and `/etc/ssl/certs/ca-certificates.crt` exists
- **THEN** that file is the bundle exposed to the container

#### Scenario: No bundle found
- **WHEN** host CA trust is enabled, `CLAUDE_CONTAINER_CA_BUNDLE` is unset, and neither default path exists
- **THEN** the wrapper exits with a non-zero status and prints an error asking the user to set `CLAUDE_CONTAINER_CA_BUNDLE`

#### Scenario: Explicit bundle path missing
- **WHEN** host CA trust is enabled and `CLAUDE_CONTAINER_CA_BUNDLE` names a file that does not exist
- **THEN** the wrapper exits with a non-zero status and prints an error naming the variable and the path, and no container is started

### Requirement: Read-only bundle mount
When host CA trust is enabled, the wrapper SHALL mount only the selected bundle file into the container, read-only, at a fixed path. It SHALL NOT mount the host certificate directory and SHALL NOT make the host trust store writable from the container.

#### Scenario: Bundle mounted read-only
- **WHEN** host CA trust is enabled
- **THEN** the container sees the selected bundle at the fixed path with read-only access, and the image's own certificate directory remains in place

### Requirement: Tools use the mounted bundle
When host CA trust is enabled, the wrapper SHALL set `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE` and `NODE_EXTRA_CA_CERTS` to the fixed path of the mounted bundle.

#### Scenario: Environment variables set
- **WHEN** host CA trust is enabled
- **THEN** all four variables are present in the container environment and each points at the mounted bundle path
