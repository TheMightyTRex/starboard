[Help centre](../README.md) · Developers
<!-- help: dev / api -->

# Connect an AI assistant

An AI assistant, such as one in your terminal or a chat app that can run commands, can answer questions about your
server from Starboard's API: which apps are down, what is downloading, what the logs say. It uses a key of its own
that only reads, so it can read but not change anything. This page explains how to set one up safely.

## What an assistant can and cannot do

- **Off until you make a key.** Nothing can reach Starboard's API without a key, and Starboard never makes one for
  an assistant by itself.
- **Read only.** Give an assistant a **Read only** key. It can then read status, health, downloads, the Library and,
  if you tick **Logs**, the logs. It cannot approve, pause, remove or change anything.
- **Never secrets.** No answer from the API holds a password, an app's API key, a token or the set-up code, and the
  logs it reads have addresses, names and keys taken out.
- **Never settings.** No key, whatever its right, can change settings, security, Docker access, the install or
  plug-ins, or delete anything from Settings. Read [What the API covers](api-coverage.md).
- **Logged.** Every key that is refused and every change made with a key is written to the audit log, so you can check
  what an assistant did.

Letting an assistant act, asking you first each time, is not built yet. It needs its own decision.

## An assistant that speaks MCP

An assistant that speaks MCP, the Model Context Protocol, needs no instructions about addresses: it connects to
`/api/v1/mcp` and is given tools for the Library, downloads, requests, app health and disk space. It is off until
you activate **Let AI assistants connect** in **Settings**, **Security**, **API keys**, and takes only a **Read only**
key. Read [Let an AI assistant answer questions about your server](../topics/connect-an-ai-assistant-with-mcp.md), and
[MCP tools](mcp-tools.md) for what each tool gives back. The rest of this page is for assistants that call the API
themselves.

## Before you begin

- Your Starboard password.
- An assistant that can run commands or call web addresses on a computer that can open Starboard.

## Make the assistant's key

1. Go to **Settings**, then **Security**, then **API keys**, and select **Make a key**.
2. In **Name it after what will use it**, name the assistant, such as `AI assistant in the terminal`. The name shows
   in the audit log.
3. In **What it may do**, keep **Read only**.
4. In **What it may read**, tick only what it needs, such as **Apps**, **Downloads** and **System**. Tick **Logs** only
   if it should read them: logs are never included when nothing is ticked. Leave **Updates** unticked unless the
   assistant should update Starboard, apps and plug-ins for you: it is never included either, and it also needs
   **Read and manage**.
5. In **Ends**, choose **In 90 days**.
6. Enter your Starboard password, select **Make a key**, then select **Copy**.

## Give it to the assistant

Put the key in an environment variable where the assistant runs, not in the chat:

```bash
read -rs STARBOARD_KEY && export STARBOARD_KEY
export STARBOARD_URL=http://192.168.1.20:8095
```

Then tell the assistant how to use it, for example:

```text
Starboard's API is at $STARBOARD_URL/api/v1. Its description is $STARBOARD_URL/api/v1/openapi.json.
Send the header "Authorization: Bearer $STARBOARD_KEY" and never print the key.
Only use GET. Tell me what you find; do not try to change anything.
```

A good first question is "Which of my apps are not answering, and why?". The assistant reads `/api/v1/status` and
`/api/v1/health`.

## Things to note

- Do not paste the key into a chat. If it gets out, revoke it in **Settings**, **Security**, **API keys** and make
  another.
- The assistant gets only what the API answers. It cannot open Starboard's pages, which need your password.
- Each key can make up to 120 requests a minute. An assistant that asks too often gets
  [`rate_limited`](../../api/errors.md#rate_limited).

## Find out more

- [Authentication and keys](api-authentication.md)
- [What the API covers](api-coverage.md)
- [MCP tools](mcp-tools.md)
- [API reference](api-reference.md)
- [AI prompts for developers](ai-prompts-for-developers.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
