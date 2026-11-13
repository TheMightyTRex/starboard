[Help centre](../README.md) · Developers

# API quickstart

Make a key and read your first answer from Starboard's API in about 5 minutes, with curl or with Python's standard
library. A key reads, or reads and does the everyday actions of the pages, only in the areas you choose. No key
can change Starboard's settings.

## Before you begin

- Your Starboard password.
- A terminal on any computer that can open Starboard, such as the server itself. Read
  [The terminal: typing commands](../basics/the-terminal.md).
- Starboard's address. These examples use `http://192.168.1.20:8095`. Use your own.

## 1. Make a key

1. Go to **Settings**, then **Security**.
2. Find **API keys** and select **Make a key**.
3. In **Name it after what will use it**, enter a name, such as `My script`.
4. In **What it may do**, keep **Read only** unless the script must act, such as pausing downloads.
5. In **What it may see**, tick only what the script needs, or none for everything.
6. In **Ends**, choose when the key stops working.
7. Enter your Starboard password, then select **Make a key**.
8. Select **Copy**. Starboard shows the key only this once.

A key looks like `sb_read_`, six letters and numbers, another `_`, then a long secret. Keep it like a password. Read
[Authentication and keys](api-authentication.md).

## 2. Keep the key out of your commands

Put the key in an environment variable, so it is not saved in your scripts or your shell's history:

```bash
read -rs STARBOARD_KEY && export STARBOARD_KEY
```

Paste the key and press Enter. Nothing shows while you paste.

## 3. Make your first call

With curl:

```bash
curl -s -H "Authorization: Bearer $STARBOARD_KEY" http://192.168.1.20:8095/api/v1/me
```

It worked when you see your key's name, such as
`{"id":"a1b2c3","name":"My script","right":"read","scopes":[],...}`. The answer never includes the key itself.

With Python, using only the standard library:

```python
import json
import os
import urllib.request

BASE = "http://192.168.1.20:8095/api/v1"
KEY = os.environ["STARBOARD_KEY"]


def get(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


for app in get("/apps")["items"]:
    print(app["name"], app["type"])
```

## 4. Read a long list a page at a time

Lists give up to 50 items by default. Ask for 1 to 200 with `limit`. When there are more, the answer's
`next_cursor` is not `null`: send it back as `cursor` to get the next page. The answer also has a `Link` header with
the next page's address.

```bash
curl -s -H "Authorization: Bearer $STARBOARD_KEY" "http://192.168.1.20:8095/api/v1/downloads?limit=20"
curl -s -H "Authorization: Bearer $STARBOARD_KEY" "http://192.168.1.20:8095/api/v1/downloads?limit=20&cursor=bzoyMA"
```

In Python:

```python
def every(path, limit=200):
    cursor = ""
    while True:
        page = get(f"{path}?limit={limit}" + (f"&cursor={cursor}" if cursor else ""))
        yield from page["items"]
        cursor = page.get("next_cursor")
        if not cursor:
            return


for item in every("/downloads"):
    print(item.get("title"))
```

Treat a cursor as a code: do not build one yourself. A cursor Starboard did not give answers
[`bad_request`](../../api/errors.md#bad_request).

## 5. Ask again only when it changed

Every answer has an `ETag` header. Send it back in `If-None-Match`. When nothing has changed, Starboard answers
`304` with no body, so your script has nothing new to read.

```bash
curl -s -D - -o /dev/null -H "Authorization: Bearer $STARBOARD_KEY" http://192.168.1.20:8095/api/v1/status | grep -i etag
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $STARBOARD_KEY" \
  -H 'If-None-Match: W/"3f1a9c2e7b5d8a0c4e6f"' http://192.168.1.20:8095/api/v1/status
```

The second command prints `304` while nothing has changed. Use the `ETag` the first command printed.

Each answer's `Cache-Control` also says how many seconds it stays fresh, such as 15 seconds for `/status`. Asking
more often than that gives the same answer.

## 6. When something goes wrong

Errors are JSON problem details, with a `code` your script can check:

```json
{"type": "https://github.com/TheMightyTRex/starboard/blob/main/docs/api/errors.md#key_needed",
 "title": "Send a Starboard API key as Authorization: Bearer sb_...", "status": 401,
 "detail": "Send a Starboard API key as Authorization: Bearer sb_...", "instance": "4c1d...", "code": "key_needed"}
```

`instance` is the request's id, also in the `X-Request-Id` header. The [list of API errors](../../api/errors.md)
explains each code and its fix. In Python, `urllib.request` raises `urllib.error.HTTPError` for these; read its body
with `json.load(e)`.

## Find out more

- [API reference](api-reference.md)
- [Authentication and keys](api-authentication.md)
- [List of API errors](../../api/errors.md)
- [API changelog](api-changelog.md)
- [AI prompts for developers](ai-prompts-for-developers.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
