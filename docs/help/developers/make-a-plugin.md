[Help centre](../README.md) · Developers

# Make your first plug-in

This tutorial builds a tiny plug-in, Hello card, from nothing. It is a small Python program with no extra
libraries. It answers Starboard's health check and one dashboard card that says how long it has been running. You
test it with the plug-in tester, then add it to your own Starboard. It takes about 20 minutes.

For what a plug-in is and what it can add, read [Write a plug-in](../basics/write-a-plugin.md) first. Every field
used here is in the [Plug-in manifest reference](plugin-manifest-reference.md).

## Before you begin

- A Starboard you can sign in to, with access to Docker. Read
  [Change what Starboard can access](../topics/change-what-starboard-can-access.md) if it has none.
- A terminal on the server, with Docker and Python 3. Read [The terminal: typing commands](../basics/the-terminal.md).
- A text editor.

## 1. Make the folder

Make a folder called `hello-card` with three files in it:

```text
hello-card/
  server.py               the plug-in itself
  Dockerfile              how to build its container
  starboard-plugin.json   the manifest Starboard reads
```

## 2. Write the program

Put this in `server.py`. It uses only Python's standard library. It answers two paths: `/health`, which Starboard
can check, and `/card`, which gives the card's number.

```python
"""Hello card: a tiny Starboard plug-in. It answers /health and one stat card at /card."""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STARTED = time.time()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            return self.answer(200, {"ok": True})
        if self.path == "/card":
            seconds = int(time.time() - STARTED)
            return self.answer(200, {"value": seconds, "label": "running", "note": "Since the plug-in last started"})
        return self.answer(404, {"error": "Not found"})

    def answer(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass  # keep the container's log quiet


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
```

Try it on its own first:

```bash
python3 server.py
```

In a second terminal:

```bash
curl -s http://127.0.0.1:8080/card
```

It worked when you see an answer such as `{"value": 12, "label": "running", "note": "Since the plug-in last started"}`.
Press Ctrl+C in the first terminal to stop it.

## 3. Describe its container

Put this in `Dockerfile`. Starboard runs every plug-in container read only, as a user that is not root, with no
extra rights, so the program must not need to write anywhere but `/tmp` or a `data` folder.

```dockerfile
FROM python:3.13-alpine
COPY server.py /app/server.py
ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8080
CMD ["python", "/app/server.py"]
```

## 4. Write the manifest

Put this in `starboard-plugin.json`. Change `author` to your public name. The `image` line is a placeholder until
step 6.

```json
{
  "manifest_version": 1,
  "id": "hello-card",
  "name": "Hello card",
  "version": "0.1.0",
  "description": "Shows on your dashboard how long it has been running.",
  "author": "Sam",
  "licence": "MIT",
  "homepage": "https://example.invalid/hello-card",
  "support_url": "https://example.invalid/hello-card/issues",
  "starboard_api": ">=1.0 <2.0",
  "permissions": [],
  "containers": [
    {"name": "main", "image": "127.0.0.1:5000/hello-card:0.1.0", "port": 8080}
  ],
  "health": "/health",
  "cards": [
    {"id": "uptime", "title": "Hello card", "type": "stat", "path": "/card", "format": "duration",
     "example": {"value": 3600, "label": "running", "note": "Since the plug-in last started"}}
  ]
}
```

What each part does:

- `permissions` is empty: Hello card reads nothing from Starboard and reaches nothing outside its own network.
- `containers` has one container. Starboard always calls the first container, on its `port`.
- `cards` adds one `stat` card. `format` is `duration`, so Starboard shows the seconds as a time. `example` is
  what `/card` answers; the tester checks it has the right shape.

## 5. Test it

The tester checks the manifest against Starboard's rules, accessibility always included, and says how to fix each
issue.

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Test a plug-in**, choose your `starboard-plugin.json`.
3. Select **Allow images without a digest (while you develop it)**, because the image is not pinned yet.
4. Select **Test it**.

Or, in a folder with Starboard's files, run:

```bash
python3 -m starboard.plugin_tester --dev path/to/hello-card
```

It worked when it says there are 0 errors. The warning that the image is not pinned by digest is expected until
step 6.

## 6. Build it and pin it by digest

Starboard installs only images pinned by digest, `name@sha256:...`, so what you test is exactly what runs. The
tester's development box allows a tag only while you test. The quickest way to get a digest on your own server is a
small registry that only the server can reach:

```bash
docker run -d --name registry --restart unless-stopped -p 127.0.0.1:5000:5000 registry:2
cd hello-card
docker build -t 127.0.0.1:5000/hello-card:0.1.0 .
docker push 127.0.0.1:5000/hello-card:0.1.0
docker inspect --format '{{index .RepoDigests 0}}' 127.0.0.1:5000/hello-card:0.1.0
```

The last command prints the pinned name, such as
`127.0.0.1:5000/hello-card@sha256:4f9c2e7d1a6b8c3e5f0a9d2b7c4e1f6a8b3d5c0e2f7a9b4d6c1e8f3a5b0d7c2e`. Put it in
`image` in the manifest, then test again without the development box. It worked when it says
**Ready to add**, or 0 errors.

When you share the plug-in, push the image to a public registry instead and pin that digest. Read
[Test and publish a plug-in](test-and-publish-a-plugin.md).

## 7. Add it to your Starboard

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Add one from elsewhere**, choose your `starboard-plugin.json` in **Or its manifest file**.
3. Select **See what it does**. Read what it may do: for Hello card, it reaches only Starboard.
4. Select **Install** and its name, and enter your Starboard password.
5. In **Settings**, then **Plug-ins**, then **Manage**, select **Activate** next to Hello card.
6. On the dashboard, select **Edit dashboard** and add the Hello card card.

It worked when the card shows how long Hello card has been running. Starboard asks `/card` at most once a minute,
and only while a dashboard with the card is open.

## 8. Change it

1. Change `server.py`, then build, push and pin again, as in step 6.
2. Raise `version` in the manifest, such as `0.1.1`.
3. While you develop, select **Remove** on the plug-in's tab, then add the new manifest as in step 7. Its old
   folder is kept in `data/plugins/.removed`.

Once the plug-in is in a catalogue, Starboard offers **Update to** and the new version on its tab, and keeps the
version before for **Roll back**. Read [Updates and Roll back](plugin-api-reference.md#updates-and-roll-back).

## If it does not work

- **"Address already in use" in step 2:** another program uses port 8080. Change `8080` in `server.py` and `port`
  in the manifest to another number, such as `8081`.
- **The card says "No answer from Hello card":** the container is not running, or `/card` answered something that
  is not the shape of a `stat` card. Check `docker logs plugin-hello-card-main`.
- **"image must be pinned by digest":** use the `name@sha256:...` from step 6, not the tag.
- **"It did not start":** read the message under the plug-in in **Manage**. A program that writes outside `/tmp`
  stops, because the container is read only.

## Find out more

- [Write a plug-in](../basics/write-a-plugin.md)
- [Plug-in manifest reference](plugin-manifest-reference.md)
- [Plug-in API reference](plugin-api-reference.md)
- [Test and publish a plug-in](test-and-publish-a-plugin.md)
- [AI prompts for developers](ai-prompts-for-developers.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
