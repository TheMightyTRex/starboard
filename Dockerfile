# Starboard: Python's standard library, plus Pillow (open source, see THIRD-PARTY.md) for white Live TV logos.
# Pillow is optional: where no ready-made Pillow exists (such as 32-bit Raspberry Pi), the image builds without it
# and channels keep their own logos. Nothing is compiled, so every build stays small and quick.
FROM python:3.12-alpine
LABEL org.opencontainers.image.source="https://github.com/TheMightyTRex/starboard"

# tzdata: download hours follow the server's local time (TZ).
RUN apk add --no-cache tzdata \
 && (pip install --no-cache-dir --only-binary=:all: "pillow==13.0.0" \
     || echo "No ready-made Pillow for this processor: white logos are off") \
 && pip uninstall -y -q pip  # not needed to run Starboard, and one less thing to keep patched

RUN addgroup -S -g 10001 starboard && adduser -S -u 10001 -G starboard -H -h /app starboard \
 && mkdir -p /data && chown starboard:starboard /data && chmod 700 /data

WORKDIR /app
COPY --chown=root:root VERSION ./
COPY --chown=root:root starboard ./starboard
COPY --chown=root:root web ./web
# Compiled once here, so Python does not compile Starboard again at every start (start-up 430 ms to 204 ms), then
# readable by the app's user whatever permissions the files had on the host. (COPY --chmod would save a layer but
# needs a newer Docker than some servers that build this image have.)
RUN python -m compileall -q -j 0 /app/starboard && chmod -R a+rX,go-w /app

ENV STARBOARD_PORT=8095 \
    STARBOARD_DATA=/data \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER starboard
EXPOSE 8095
HEALTHCHECK --interval=60s --timeout=5s --start-period=10s \
  CMD wget -q -O /dev/null http://127.0.0.1:${STARBOARD_PORT}/healthz || exit 1
CMD ["python", "-m", "starboard"]
