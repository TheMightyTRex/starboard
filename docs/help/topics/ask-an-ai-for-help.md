[Help centre](../README.md) · Before you install · how-to

# Ask an AI assistant to help you set up

An AI assistant, such as Claude or ChatGPT, can walk you through setting up Starboard, read error messages with you
and explain what each command does. Copy one of the prompts below into it, fill in the parts in square brackets,
and it follows Starboard's own help with you, one step at a time.

## Before you begin

- An AI assistant you already use, in a browser or app on your phone or another computer, or one installed on the
  server itself.
- Starboard's help centre is the final word. If the assistant says something different, follow the help centre.

## Steps

1. Choose the prompt that fits:
   - **An assistant in a chat**, on your phone or another computer: it tells you what to type, and you copy the
     result back to it.
   - **An assistant on the server**, one that can run commands in the server's terminal for you.
2. Copy the whole prompt, fill in the parts in square brackets, and send it.
3. Do one step at a time. When the assistant asks, copy what the terminal printed back to it.

### For an assistant in a chat

```text
Help me set up Starboard, a lightweight dashboard and installer for a home media server
(https://github.com/TheMightyTRex/starboard). Follow its help centre, starting with the guide
"Get Starboard up and running, from a bare computer":
https://github.com/TheMightyTRex/starboard/blob/main/docs/help/guides/get-up-and-running.md

About me:
- My server computer: [make and model, or "a Raspberry Pi 4"], with [amount] of memory.
- It runs: [nothing yet / Debian 13 / Ubuntu / Linux Mint / Raspberry Pi OS].
- I want to finish set-up: [in a browser / in the terminal only].
- I have used a terminal: [never / a little / often].

How to help me:
- One step at a time. Tell me the exact command, what it does in one sentence, and how I will know it worked.
- Wait for me to paste what the terminal printed before the next step.
- Use the commands in Starboard's help pages. If you suggest something else, say so and why.
- Never ask for my passwords or API keys, and tell me to remove them if I paste one by mistake.
- Never suggest opening a port on my router or turning off the firewall. For access away from home, use
  Starboard's guide "Use Starboard away from home safely".
- Use plain words. Explain any technical word the first time.
```

### For an assistant on the server

Only use an assistant on the server that shows you each command and waits for your yes before running it.

```text
You are on my home server, helping me set up Starboard, a lightweight dashboard and installer for a home
media server (https://github.com/TheMightyTRex/starboard). Follow its help centre, starting with the guide
"Get Starboard up and running, from a bare computer":
https://github.com/TheMightyTRex/starboard/blob/main/docs/help/guides/get-up-and-running.md
I want to finish set-up: [in a browser / in the terminal only].

Before you change anything:
- Check what is already here and tell me: the Linux version, memory, free disk space, and whether Docker
  and Starboard are installed (docker compose version; docker ps).

Rules for every step:
- Show me each command and say in one sentence what it does, then wait for my yes before running it.
- After each step, check its "It worked when" line from the help, and tell me the result.
- Never type or store my passwords. When a command asks for one (such as sudo), stop and let me type it.
- Ask me first before anything that deletes files, formats or mounts a disk, changes the firewall, or
  changes how the server starts. Never touch disks or folders I have not named.
- Never open ports on my router or expose the server to the internet.
- Run Starboard's installer as my normal user, not with sudo, as its help says.
- If a step fails, stop, show me the error, and suggest the fix from the help's "If it does not work" section.
- At the end, list what you changed, so I can keep a note of it.
```

## Things to note

- An AI assistant can be wrong with confidence. Check each command against the help page it came from before you
  run it.
- What you paste into a chat assistant leaves your network. Remove passwords, API keys and your home address on
  the internet before you paste anything.

## Find out more

- [Get Starboard up and running, from a bare computer](../guides/get-up-and-running.md)
- [The terminal: typing commands](../basics/the-terminal.md)
- [Send feedback about a page](send-feedback.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
