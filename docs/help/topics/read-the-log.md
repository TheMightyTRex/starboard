[Help centre](../README.md) · When something is wrong · how-to

# Read the log and report a problem

Starboard's log lists what it did and every problem it met, newest first. When something goes wrong, the
**Report a problem** steps gather the details a bug report needs, with personal details removed.

## Steps

### Read the log

1. Go to **System**, then **Logs**.
2. In **Log**, choose what to show:
   - **Everything**: every entry.
   - **Problems**: errors and warnings only.
   - **Detailed**: the extra entries detailed logging adds.
3. To find something, enter a word in **Search the log**, such as the name of an app.

Each entry shows its **Time**, its **Level** (Error, Warning, Info or Detail), the **Area** of Starboard it
came from and **What happened**. Select an entry's message to show more, when it has more. Select
**Show older entries** to go further back.

### Report a problem

1. Go to **System**, then **Logs**, and find **Report a problem**.
2. In **Detailed logging**, choose **For 24 hours**. This records every page request and every call to your
   apps.
3. Do the thing that went wrong again.
4. Select **Copy the details**. Starboard shows "Copied. Paste it into the issue".
5. Select **Open a new issue on GitHub**. Paste the details into the issue, and say what you expected to
   happen.
6. When you have finished, set **Detailed logging** back to **Off**.

To check what will be copied before you share it, select **Show what will be copied**.

## Things to note

- Starboard removes personal details before anything is written to its log: passwords, API keys and tokens,
  IP addresses, host and computer names, email addresses, the user name in folder paths and the dashboard's
  name. Read the text before you post it all the same.
- **Download** saves the whole log as a text file, for example to attach it to an issue.
- To suggest something or report a problem with one page, use **Feedback** in the side menu instead. Read
  [Send feedback about a page](send-feedback.md).
- **Delete logs** removes every day of the log. Starboard asks **Delete all logs?** first. This cannot be
  undone, and new entries start again straight away.
- Starboard keeps the log for 60 days unless you change it. Go to **Settings**, then **General**, and choose in
  **Keep logs for**, in the **Logs** section. That section also has **Detailed logging**.
- If Starboard installed Reelix, **System**, **Logs** also has **Reelix's log** and **Reelix's scheduled tasks**.
  Starboard asks for Reelix's password first.
- If you cannot open Starboard at all, read the server's copy of the log. On the server, in the Starboard
  folder, run this command:

  ```bash
  docker compose logs starboard
  ```

  Then read [Starboard does not open](starboard-does-not-open.md).

## If it does not work

- **"Could not copy. Use Download instead":** your browser did not allow copying. Select **Download**, then
  attach the file or copy the text from it.
- **"Set STARBOARD_REPO on the server to link straight to the issue page":** Starboard does not know where
  to report problems. Go to the Starboard project on GitHub and open a new issue there.

## Find out more

- [Starboard does not open](starboard-does-not-open.md)
- [An app shows as not responding](app-not-responding.md)
- [Send feedback about a page](send-feedback.md)
- [Activate alerts](activate-alerts.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
