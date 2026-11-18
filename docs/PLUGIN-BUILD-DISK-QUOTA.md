# Plug-in build disk isolation: implementation requirements

Status: architecture selected; implementation pending. See [the accepted architecture decision](PLUGIN-BUILD-ISOLATION-ADR.md) in PR #194.

The selected design is a disposable Buildx `docker-container` BuildKit instance with its state, intermediate layers and exported archive stored under an 8 GiB host-provisioned XFS project quota. BuildKit GC is a secondary cleanup mechanism only. The host quota is the hard boundary. The exported image archive is checked by expanded layer size before import into the shared Docker daemon.

The installer must provision and verify the quota-backed mount at `/var/lib/starboard-builds`. Hosts without the supported mount refuse zip builds safely; there is no fallback to the daemon's shared data root.

## Current boundary

A zip upload is capped at 50 MB and 200 MB unpacked, the build context is made only from those checked files, and the
Docker build is limited to 2 GB memory, 2 CPUs and 20 minutes. Starboard refuses and removes a final image larger than
3 GB. These limits do not cap temporary build layers or the builder cache while a `RUN` instruction is executing.

The legacy Docker Engine image-build endpoint used by `starboard/plugin_zip.py` exposes CPU and memory limits, but no
per-build storage quota. A check of free space before or after the build is only a warning: it cannot stop a build from
filling the Docker data root in the meantime. `docker system df` is also an observation, not an enforcement boundary.

## Required design

Use a disposable, per-build builder whose storage is on a quota-capable filesystem. The quota must cover both the
intermediate layers and the final image, be enforced by the host filesystem or builder (not by polling), and be removed
when the build succeeds, fails, times out or Starboard restarts. The final image must be exported only after it passes
the 3 GB final-image limit. A failed or interrupted build must not leave unbounded cache behind.

The design must work on supported Docker installations or explicitly detect and explain when the host cannot provide
the required isolation. Do not claim a disk quota based on context size, free-space checks, `docker system df`, or the
final image size alone.

## Acceptance tests

- A Dockerfile that writes beyond the configured build quota is stopped before the host Docker data root is exhausted.
- The quota applies to intermediate layers and build cache, not just the final image.
- Successful builds retain only the tagged image; failed builds remove the disposable builder and its storage.
- Concurrent normal Docker workloads and existing images are not deleted or charged to the plug-in's quota.
- Tests cover cancellation, daemon restart and cleanup failure.
