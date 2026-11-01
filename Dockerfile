# Starboard: standard library Python only, so there are no third-party packages to keep patched.
FROM python:3.12-alpine

RUN addgroup -S -g 10001 starboard && adduser -S -u 10001 -G starboard -H -h /app starboard \
 && mkdir -p /data && chown starboard:starboard /data && chmod 700 /data

WORKDIR /app
COPY --chown=root:root VERSION ./
COPY --chown=root:root starboard ./starboard
COPY --chown=root:root web ./web

ENV STARBOARD_PORT=8095 \
    STARBOARD_DATA=/data \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER starboard
EXPOSE 8095
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD wget -q -O /dev/null http://127.0.0.1:${STARBOARD_PORT}/healthz || exit 1
CMD ["python", "-m", "starboard"]
