[Help centre](../README.md) · Security · how-to
<!-- help: use / security -->

# Connect an AI tool to Starboard

An AI tool, such as Claude Desktop or Claude Code, can ask Starboard about your server for you: "Which of my apps have
a problem?", "What is downloading?", "How full are my disks?". A wizard in Settings turns this on, makes a key for the
tool, and gives you the exact steps to paste. The tool can read what you choose. It cannot change anything.

Nothing runs by itself and nothing costs anything. Starboard answers only when a tool asks, from what it already
knows. It does not include an AI model: the AI tool you connect brings its own.

## What a tool can and cannot do

- **It can read** what you tick in the wizard: your apps and their problems, downloads, what is new and playing, disk
  space and, only if you tick them, the Library, requests, logs and which updates wait.
- **It can never** change anything, read a password, an app's key, a token or the set-up code, reach another computer,
  make another key or turn AI tools on or off.
- **Private details are hidden** before a tool reads anything: keys and tokens are removed, and email addresses, network
  addresses, host names, folder names and the names of your people are replaced by markers such as `[address 1]`.
- **Every answer is marked as data.** Logs and app messages are written by apps and other people, so a line in a log that
  says "ignore your rules" is only text. Starboard says so in each answer.
- **Everything is written down.** The audit log records when a key is made, used and revoked and each question a tool
  asks, with the tool's name and whether it worked. It never records what was asked or answered.

## Before you begin

- Your Starboard password.
- An AI tool that can connect to an MCP server over HTTP, on a computer that can reach Starboard. What MCP means is
  explained in the wizard.
- For a tool away from home, Tailscale on the server and on that computer. Read [Reach Starboard away from home](#reach-starboard-away-from-home).

## Steps

### Make the key

1. Go to **Settings**, then **Security**, then **Connect an AI tool**.
2. Under **Which AI tool will you connect?**, choose **Claude Desktop**, **Claude Code** or **Another MCP tool, such as
   Goose or Jan**, then select **Continue**.

   If your tool says it is OpenAI compatible, read the note under the choices: Starboard speaks MCP, not the OpenAI
   language, so use a tool that speaks MCP.
3. Under **Where does the AI tool run?**, choose **On this server**, **On another computer in my home** or **Away from
   home, over Tailscale**. For Tailscale, enter your server's Tailscale name, which ends in `.ts.net`. Select **Continue**.
4. Under **What may the AI tool read?**, keep the ticks you need. Your apps, Downloads, What is new and playing and Disk
   space are ticked. Library, Requests, Logs and Updates are not, so tick one only when the tool needs it. Select **Continue**.
5. Under **When should the key stop working? (optional)**, keep **In 90 days**, or choose another. Select **Continue**,
   or **Skip this step** to keep 90 days.
6. Under **What should the key be called? (optional)**, name it after the tool and the computer, such as `Claude Desktop on
   the laptop`. Select **Continue**, or **Skip this step** to keep the suggested name.
7. On **Check your answers**, read each answer. Select **Change** beside one to go back to it, and you come straight back
   to the answers. Starboard also lists what the key will and will never be able to do.
8. Enter your Starboard password, then select **Turn on AI tools and make the key**. If AI tools are already on, the
   button says **Make the key**.

### Copy the address and the key

1. The result page shows the **Address** and the **Key**. Select the copy button beside the address.
2. Select **Show** if you want to read the key, then **Copy** to copy it. Starboard shows the key only now and keeps
   only a scrambled copy, so it cannot show it again. If you lose it, revoke the key and make another.
3. Select **Check that it answers**. Starboard asks itself, with the new key, which tools it can use, and says how many.
   This checks the key from this page, not the path from your other computer.

### Set up the tool

The result page gives the steps for the tool you chose, with lines to copy. In short:

- **Claude Desktop:** open **Settings**, **Developer**, **Edit config**, add the block the wizard shows, save, quit Claude
  Desktop completely and open it again. It reaches Starboard through a small helper called `mcp-remote`, which needs
  Node.js on the same computer. If your address starts with `http`, add `--allow-http` after the address in `args`.
- **Claude Code:** in a terminal, run the first line, which asks for the key without showing it, then the second:

  ```bash
  read -rs STARBOARD_KEY && export STARBOARD_KEY
  claude mcp add --transport http starboard http://192.168.1.20:8095/api/v1/mcp \
    --header "Authorization: Bearer $STARBOARD_KEY"
  ```

  Start `claude` and use `/mcp` to check that `starboard` shows as connected.
- **Goose, Jan and other MCP tools:** add an MCP server of the kind **Streamable HTTP** or **Remote**. Enter the address
  and one header, `Authorization`, with `Bearer`, a space and the key. For Goose, the wizard also gives an extension block
  for its config file.

Then ask the tool a question, such as "Which of my apps have a problem?".

### Reach Starboard away from home

Use Tailscale Serve. It shares Starboard only with your own devices, over HTTPS.

1. Install Tailscale on the server and on the computer that runs the AI tool. Sign in to the same account on both.
2. On the server, run `tailscale serve --bg 8095`. Use your own port if Starboard does not use 8095.
3. Run `tailscale serve status`. It shows your server's name, which ends in `.ts.net`. Enter it in the wizard.
4. Tell Starboard the name. In the `.env` file in the Starboard folder, add it to `STARBOARD_ALLOWED_HOSTS`, then run
   `docker compose up -d`. Without this Starboard answers 421. Read [Put Starboard behind a reverse proxy](reverse-proxy.md) for the file.
5. Run `tailscale funnel status`. It should say Funnel is off.

**Never use Tailscale Funnel for Starboard, and never open port 8095 on your router.** Both put Starboard on the public
internet, where anyone can try to reach it. The wizard has no public address option on purpose. Starboard does not
offer a connector for claude.ai in a browser, because that would need Starboard on the public internet.

## Manage the keys

Settings, Security, Connect an AI tool lists each key made here, with its name, the tool, whether it was used and when it
ends. Select **Revoke** beside a key to stop it at once, then confirm. **What AI tools did lately** shows the newest lines of
the audit log about AI tools. **Turn off AI tools** stops every tool at once, whatever key it has.

## Things to note

- **One key for each tool.** If a laptop is lost, revoke only its key.
- **If a tool says Starboard refused it,** check that AI tools are on, that the key has not ended or been revoked, and
  that the address is right. A key that may manage is refused: the wizard only makes keys that read.
- **If a tool says it has no tool for logs,** the key was made without **Logs** ticked. Make another key with it ticked.
- **Rate limit.** Each key may ask up to 120 times a minute.
- **Lightweight.** Nothing runs while no tool asks. Each answer comes from the same saved answers as the pages.

## Find out more

- [Let an AI assistant answer questions about your server](connect-an-ai-assistant-with-mcp.md), the older steps by hand
- [MCP tools, for developers](../developers/mcp-tools.md)
- [Make an API key and use Starboard's API](use-starboards-api.md)
- [Use Starboard away from home safely](../guides/use-starboard-away-from-home.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
