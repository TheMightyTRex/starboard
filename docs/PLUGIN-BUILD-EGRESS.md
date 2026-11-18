# Plug-in build network isolation: implementation requirements

Status: design decision required. This note records the security boundary needed before changing the current build
network mode.

## Current boundary

Plug-in Dockerfiles are checked to reject host networking and elevated build mounts, but build steps currently use the
Docker builder's default network. Public package repositories are needed by legitimate `RUN` instructions, so changing
the build network to `none` would break common `apt`, `apk`, `pip` and `npm` installs. Leaving the default network in
place allows a build step to attempt connections to host services, private LAN addresses and metadata endpoints.

## Required design

Run each build on a disposable internal-only network with no direct route to the host or internet. Provide a narrowly
scoped outbound proxy for public package downloads. The proxy must resolve the destination itself, reject loopback,
private, link-local, multicast, reserved and metadata addresses, pin the resolved address for the connection, and
repeat the checks for redirects and CONNECT requests. Build steps must not be able to bypass the proxy with direct IP
connections or alternate DNS.

The proxy must not expose Starboard's HTTP/API listener or Docker socket to build containers. Its lifecycle must be
bound to the build and cleanup must happen on success, failure, timeout or Starboard restart. Do not use host networking,
share the application container's network namespace, or rely on Docker's default bridge as an egress control.

## Acceptance tests

- A build can fetch packages from a public test repository through the proxy.
- Direct IPv4/IPv6, private-LAN, host-gateway, loopback and cloud metadata requests fail from `RUN`.
- DNS answers that change between validation and connection cannot redirect the proxy to a blocked address.
- Redirects and HTTPS CONNECT are subject to the same policy.
- Build containers cannot connect to Starboard, the Docker socket, or other host services.
- Cleanup removes the temporary network and proxy after every terminal build state.
