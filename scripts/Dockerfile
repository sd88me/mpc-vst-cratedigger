# Compilers for the SDK front end: native x86 (offline test), armhf glibc 2.31 (Force and the other 32-bit MPCs), arm64 (Live III).
#   docker build -q -t crate-sdk-x64 --build-arg BASE=gcc:12 scripts
#   docker build -q -t crate-sdk-arm32 --platform linux/arm/v7 --build-arg BASE=arm32v7/gcc:11-bullseye scripts
#   docker build -q -t crate-sdk-arm64 --platform linux/arm64 --build-arg BASE=arm64v8/gcc:12-bookworm scripts
ARG BASE=gcc:12
FROM ${BASE}
