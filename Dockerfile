# Starboard: Python's standard library, plus Pillow (open source, see THIRD-PARTY.md) for white Live TV logos, and
# cryptography (open source, see THIRD-PARTY.md) to encrypt full backups (DASH-260); it is loaded only while one is made.
# Pillow is optional: where no ready-made Pillow exists (such as 32-bit Raspberry Pi), the image builds without it
# and channels keep their own logos. Nothing is compiled, so every build stays small and quick.
FROM python:3.12-alpine AS system

# tzdata: download hours follow the server's local time (TZ). apk upgrade: every package of the base image takes
# Alpine's fixed version at build (zlib's CVE-2026-4738 on 8 November 2026; krb5-libs, 16 high CVEs fixed in
# 1.22.3, on 11 November 2026), so a fix in Alpine reaches the next build with no change here.
# pip is not needed to run Starboard, and is one less thing to keep patched; nor are these parts of Python's standard
# library: pip's own copy in ensurepip, the IDLE editor, 2to3, help() texts, Tk windows, the turtle demos and the
# files for building C extensions. Nothing in Starboard imports them.
RUN apk upgrade --no-cache && apk add --no-cache tzdata \
 && (pip install --no-cache-dir --only-binary=:all: "pillow==13.0.0" \
     || echo "No ready-made Pillow for this processor: white logos are off") \
 && (pip install --no-cache-dir --only-binary=:all: "cryptography==50.0.2" \
     || echo "No ready-made cryptography for this processor: full backups cannot be made here") \
 && pip uninstall -y -q pip \
 && L=/usr/local/lib/python3.12 \
 && rm -rf "$L/ensurepip" "$L/idlelib" "$L/lib2to3" "$L/pydoc_data" "$L/tkinter" "$L/turtledemo" "$L/turtle.py" \
           "$L"/__pycache__/turtle.* "$L"/config-3.12-* "$L"/lib-dynload/_tkinter.* /usr/local/bin/idle3* \
           /usr/local/bin/pydoc3* /usr/local/bin/2to3* \
 && addgroup -S -g 10001 starboard && adduser -S -u 10001 -G starboard -H -h /app starboard \
 && mkdir -p /data && chown starboard:starboard /data && chmod 700 /data

# The system above as one layer. Removing files in a later layer only hides them (the base image's layers still
# hold them), and apk upgrade kept a second copy of every package it replaced: one layer keeps neither.
FROM scratch
COPY --from=system / /
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=C.UTF-8
LABEL org.opencontainers.image.source="https://github.com/TheMightyTRex/starboard"

WORKDIR /app
COPY --chown=root:root VERSION ./
COPY --chown=root:root starboard ./starboard
COPY --chown=root:root web ./web
# Plug-ins that ship inside Starboard, such as Live TV (DASH-285).
COPY --chown=root:root plugins ./plugins
# Compiled once here, so Python does not compile Starboard again at every start (start-up 430 ms to 204 ms), then
# readable by the app's user whatever permissions the files had on the host. Only files whose permissions are wrong
# are changed: a chmod of every file copied all of them into this layer a second time (about 10 MB). (COPY --chmod
# would do it with no layer but needs a newer Docker than some servers that build this image have.)
RUN python -m compileall -q -j 0 /app/starboard \
 && find /app -type d \( ! -perm -555 -o -perm /022 \) -exec chmod a+rx,go-w {} + \
 && find /app -type f \( ! -perm -444 -o -perm /022 \) -exec chmod a+r,go-w {} +

ENV STARBOARD_PORT=8095 \
    STARBOARD_DATA=/data \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER starboard
EXPOSE 8095
HEALTHCHECK --interval=60s --timeout=5s --start-period=10s \
  CMD wget -q -O /dev/null http://127.0.0.1:${STARBOARD_PORT}/healthz || exit 1
CMD ["python", "-m", "starboard"]
