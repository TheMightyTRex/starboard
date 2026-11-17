# The code and writing checks (tools/checks.sh), in one small image so they run the same here and on GitHub.
# Each tool is pinned to a version, and each image it is copied from to a digest.
FROM rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667 AS actionlint
FROM jdkato/vale:v3.26.0@sha256:d4ebc402b255dacc759c468ed8c91bd5be82918bbb59583558539f3be80f1f01 AS vale
FROM ghcr.io/biomejs/biome:2.6.8@sha256:0eecaa0c37167e816b75ea0c7b97fef12a9b868ea56ca86e32873ff6eccd87b5 AS biome
FROM python:3.12-alpine
RUN apk add --no-cache libstdc++ libgcc git && pip install --no-cache-dir --root-user-action=ignore ruff==0.17.5 typos==1.52.2 zizmor==1.32.0 coverage==7.17.3
COPY --from=actionlint /usr/local/bin/actionlint /usr/local/bin/actionlint
COPY --from=vale /bin/vale /usr/local/bin/vale
COPY --from=biome /usr/local/bin/biome /usr/local/bin/biome
WORKDIR /src
# Never root, and a one-off tool with nothing to check the health of (tools/checks.sh runs it as your own user anyway).
USER 10001:10001
HEALTHCHECK NONE
