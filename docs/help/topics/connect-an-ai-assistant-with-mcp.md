[Help centre](../README.md) · Security · how-to
<!-- help: use / security -->

# Let an AI assistant answer questions about your server

An AI assistant that speaks MCP, the Model Context Protocol, can ask Starboard about your media server for you: "Is
the new series downloading?", "Which apps have a problem?", "How much space is left?". It reads only, with a key you
make for it, and only once you activate **Let AI assistants connect**. It cannot change anything.

## What an assistant can read

- The Library: films, series, music, books and audiobooks, by title or name. This needs Reelix.
- What was added in the last 7 days, what is coming up, and what is playing in Jellyfin.
- What is downloading, and downloads that need attention or failed.
- Requests from Seerr or Reelix, and how many wait for an answer.
- Whether each app answers, and the problems the apps report.
- The size, the space used and the space free on each disk Starboard watches.

It never gets a password, an app's API key, a token or a private address, and it reads only what its key's
scopes cover. Each question it asks is written to the audit log. Approving requests or pausing downloads from an
assistant is not built yet.

## Before you begin

- Your Starboard password.
- An AI assistant that speaks MCP over HTTP and runs on a computer that can open Starboard, such as one on the
  server or on a computer at home. Starboard does not need to be on the internet for this, and it is safer when it
  is not.

## Steps

### Activate AI assistants

1. Go to **Settings**, then **Security**, then **API keys**.
2. Under **AI assistants**, activate **Let AI assistants connect**. Starboard says **Active** and shows the
   **Address for the assistant**, such as `http://192.0.2.10:8095/api/v1/mcp`.
3. Select the copy button beside the address.

### Make the assistant's key

1. On the same page, select **Make a key**. A slide-out opens.
2. In **Name it after what will use it**, enter the assistant's name, such as `AI assistant`. The name shows in the
   audit log.
3. In **What it may do**, keep **Read only**. Starboard refuses a key that may also manage.
4. In **What it may read**, tick only what the assistant needs, such as **Apps**, **Downloads** and **System**.
5. In **Ends**, choose **In 90 days**.
6. In **Your Starboard password**, enter the password, then select **Make a key**.
7. Select **Copy**. Starboard shows the key only this once. Select **Done**.

### Add Starboard to the assistant

Each assistant adds an MCP server in its own way. Give it three things:

- **The kind of connection:** HTTP, sometimes called Streamable HTTP.
- **The address:** the one you copied, ending `/api/v1/mcp`.
- **A header:** `Authorization`, with `Bearer`, a space and the key.

For example, in Claude Code, in a terminal, put the key in a variable first so it is not saved in your history:

```bash
read -rs STARBOARD_KEY && export STARBOARD_KEY
claude mcp add --transport http starboard http://192.0.2.10:8095/api/v1/mcp \
  --header "Authorization: Bearer $STARBOARD_KEY"
```

Many assistants take a settings file in this form instead:

```json
{
  "mcpServers": {
    "starboard": {
      "type": "http",
      "url": "http://192.0.2.10:8095/api/v1/mcp",
      "headers": { "Authorization": "Bearer ${STARBOARD_KEY}" }
    }
  }
}
```

Then ask the assistant a question, such as "Which of my apps are not answering?".

## Things to note

- **Deactivate it at any time.** Deactivate **Let AI assistants connect** and every assistant stops at once, whatever
  key it has. Its key still works for the rest of the API until you revoke it.
- **Stop one assistant.** Revoke its key in **Settings**, **Security**, **API keys**.
- **What the assistant is told.** It gets only the tools its key's scopes cover. A key with only **Downloads**, for
  example, offers no Library search.
- **How often.** Each key can ask up to 120 questions a minute, shared with the rest of the API.
- **If the assistant says Starboard refused it,** check that **Let AI assistants connect** is active and that the
  key is **Read only**. Starboard also refuses requests from a web page on another site.
- **Lightweight.** Nothing runs until an assistant asks, and each answer comes from the same saved answers as the
  pages.

## Find out more

- [Make an API key and use Starboard's API](use-starboards-api.md)
- [How Starboard keeps your server safe](../basics/how-starboard-keeps-you-safe.md)
- [MCP tools, for developers](../developers/mcp-tools.md)
- [Connect an AI assistant to the API](../developers/connect-an-ai-assistant.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
