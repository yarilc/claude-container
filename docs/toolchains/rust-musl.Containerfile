# Rust toolchain with the musl target, for the toolchain library example.
# The runtime image has no C linker, so the example links with rust-lld.
FROM docker.io/library/rust@sha256:7c7d4eb4d05b7781187a327809466cfddf29753f6defdc3d19a0e291951b7a37
RUN rustup target add x86_64-unknown-linux-musl
