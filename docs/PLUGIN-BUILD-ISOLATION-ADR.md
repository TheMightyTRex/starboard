# Architecture decision: isolate plug-in image builds

- Status: **Accepted design; implementation pending**
- Date: 18 November 2026
- Scope: zip-installed plug-ins whose Dockerfiles Starboard builds
- Supersedes: the open design-only proposals in PRs #192 and #193

## Decision

Use a **disposable BuildKit builder created with Buildx's `docker-container` driver**, not the Docker Engine's legacy `POST /build` endpoint. Each build gets a unique workspace and builder instance. The builder is removed after the result is imported or the build fails. Do not share a persistent global BuildKit cache between untrusted plug-ins.

BuildKit is the appropriate builder because the container driver gives Starboard a separately configurable daemon, driver-level CPU and memory limits, a configurable network, and a dedicated state volume. The default Docker driver is bound to the daemon and is not manually configurable. See [Docker's driver comparison](https://docs.docker.com/build/builders/drivers/) and [container driver options](https://docs.docker.com/build/builders/drivers/docker-container/).

### 1. Hard disk boundary

BuildKit's garbage-collection `maxUsedSpace` is **not** a hard quota: it reclaims cache after a threshold is exceeded and cannot prevent one active build from filling the filesystem. See [Docker BuildKit garbage collection](https://docs.docker.com/build/cache/garbage-collection/) and [BuildKit configuration](https://docs.docker.com/build/buildkit/toml-configuration).

Therefore the host must provision a dedicated **8 GiB XFS project-quota-backed directory** for build workspaces and expose it to Starboard as `/var/lib/starboard-builds`. The quota is applied on the host, not from the Starboard container. It covers the disposable BuildKit state, intermediate layers, cache and exported image archive. Starboard remains unprivileged and must not be granted `CAP_SYS_ADMIN`, mount access, or the ability to change host quotas.

- The installer provisions and verifies the XFS mount and project quota before enabling zip-based image builds.
- On hosts without the required quota-backed mount, Starboard refuses to build a zip Dockerfile and explains how to enable the feature. It must not silently fall back to the daemon's shared storage.
- Only one untrusted zip build runs at a time, as today.
- Configure BuildKit GC below the hard quota (6 GiB target) as early cleanup, not as the enforcement boundary.
- Export a Docker-compatible archive inside the quota-backed workspace. Before loading it into the host daemon, inspect every layer and sum the **uncompressed layer sizes**; refuse an image over the existing 3 GiB limit before it consumes shared daemon image storage. Remove the workspace and builder on success, failure, timeout, cancellation and restart recovery.

### 2. Network boundary

Run the BuildKit container on a dedicated internal-only Docker network. Configure the BuildKit OCI worker with a dedicated CNI network that has no direct Internet or LAN route. Its only default route is a Starboard-managed egress proxy attached to both the isolated build network and a separate outbound network.

The proxy is the sole permitted egress path. It must:
- accept HTTP proxy requests and HTTPS CONNECT only;
- resolve names itself, reject loopback, private, link-local, multicast, reserved, and metadata-service destinations, and pin the validated address for the connection;
- re-check every new destination, redirect and CONNECT request;
- reject literal IP destinations and block DNS/direct egress from build steps;
- never expose the Docker socket, Starboard listener, host services, or credentials to the build network.

The proxy container is disposable per build, has no Docker socket, and is removed with the builder. Do not use host networking for the builder or the proxy. Build steps retain package downloads through the proxy; direct outbound connections are denied by routing/firewall policy rather than relying on Dockerfile convention or proxy environment variables alone.

Docker documents the Buildx container driver's configurable network and BuildKit's CNI bridge mode; the final implementation must add an explicit deny-by-default CNI/firewall policy and prove it with integration tests. See [container driver custom networks](https://docs.docker.com/build/builders/drivers/docker-container/) and [BuildKit network configuration](https://docs.docker.com/build/buildkit/configure/).

### 3. Resource limits and image handoff

Keep the current 2 GiB memory, 2 CPU and 20-minute build limits, but apply them to the disposable BuildKit container and its worker cgroups. The current legacy API's build-step limits are not sufficient evidence of a whole-build memory/CPU cap.

Only import an archive after:
1. the build process exits successfully within the deadline;
2. the archive is structurally valid;
3. all uncompressed layers total no more than 3 GiB;
4. the resulting image is tagged with Starboard's existing ownership labels.

Then inspect the daemon image and keep the existing final image-size check as defence in depth.

### 4. Compatibility and rollout

This is a Linux-host feature because it requires a host XFS project-quota mount and Docker Buildx/BuildKit. Do not silently degrade on older Docker installations, non-Linux hosts, or filesystems without the quota. Existing plug-ins with already-built images continue to run; only new zip builds and rebuilds of missing zip-built images are gated.

Rollout order:
1. installer creates the quota mount and binds it into Starboard;
2. Starboard verifies Buildx/BuildKit and the workspace mount before accepting a build;
3. add the disposable builder, archive verification and proxy;
4. run adversarial integration tests on a real Linux Docker host;
5. enable the feature by default only after the tests pass.

## Acceptance tests

### Storage
- A build that writes more than 8 GiB to intermediate layers is stopped by the filesystem quota before the host Docker data root is exhausted.
- The quota covers BuildKit state, intermediate layers, cache and exported archive.
- A Docker image whose expanded layers exceed 3 GiB is rejected before loading into the shared daemon image store.
- Success, failure, timeout, cancellation and Starboard restart all clean up the builder, proxy and workspace.
- Existing host images, containers and normal Docker workloads are not pruned or charged to the build quota.
- A host without the quota-backed mount is refused safely.

### Network
- Public package downloads work through the proxy.
- Direct IPv4 and IPv6 egress, private LAN, loopback, host gateway, link-local and cloud metadata destinations fail.
- DNS rebinding cannot change the address after validation.
- Redirects and HTTPS CONNECT to blocked destinations fail.
- Build steps cannot reach the Starboard listener, Docker socket, proxy management endpoint or other host services.
- The proxy cannot be bypassed with direct IP, alternate DNS, raw sockets or a different proxy variable.

### Resource limits
- CPU, memory and wall-clock limits apply to the whole disposable builder, not merely one build step.
- Concurrent zip builds remain serialized.
