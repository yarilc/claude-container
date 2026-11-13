## ADDED Requirements

### Requirement: Session variables are protected from toolchains
A toolchain SHALL NOT set a variable that the session or a wrapper owns, including every variable whose name starts with `XDG_`. `add` SHALL reject such a recipe, and `launch-env` SHALL fail instead of emitting such a variable from the index.

#### Scenario: Other session variables stay protected
- **WHEN** a recipe sets `HOME`, `PATH`, an `LD_` variable, a proxy or CA variable, the profile's configuration variable, or a variable with the wrapper's or the `SANDBOX_` prefix
- **THEN** `add` fails naming the variable as protected

#### Scenario: XDG variable in a recipe
- **WHEN** a recipe sets `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME`, `XDG_RUNTIME_DIR` or another `XDG_` variable
- **THEN** `add` fails naming the variable as protected, and the library is unchanged

#### Scenario: XDG variable in an existing index
- **WHEN** the library index lists a default toolchain with an `XDG_` variable
- **THEN** `launch-env` fails with an invalid-environment error, and the session does not start with that variable

#### Scenario: Wrapper state location kept
- **WHEN** a wrapper places its state with XDG variables, and default toolchains are installed
- **THEN** new sessions keep the wrapper's XDG values
