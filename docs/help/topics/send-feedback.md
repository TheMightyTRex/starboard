[Help centre](../README.md) · When something is wrong · how-to

# Send feedback about a page

Send feedback puts a button in the corner of every page. Use it to report something that is broken or hard to
use, suggest something, or check a page for accessibility problems. Each report says which page and which part of
it, and keeps nothing personal. It uses [Snaglist](https://github.com/TheMightyTRex/snaglist).

## Before you begin

- You are signed in to Starboard.

## Activate it

1. Go to **Settings**, then **General**.
2. Under **Testing**, activate **Send feedback**. Starboard shows **Send feedback activated on every page**.

## Send a report

1. On the page with the problem, select **Send feedback** in the corner.
2. Choose what you want to send, such as **Something is broken** or **A new feature**.
3. Choose what to show: **One thing on the page**, **A series of steps** or **Describe it in words**. For one
   thing, select the part of the page it is about.
4. Answer the questions, then select **Review what is sent**. You see the whole report, and you can untick
   anything you would rather not send.
5. Choose where it goes:
   - **Open in GitHub** opens a new issue on Starboard's GitHub page with the report filled in. You post it from
     your own GitHub account.
   - **Save in Starboard** keeps it on your server. Starboard shows **Saved in Starboard**.
   - **Copy as Markdown** or **Download** gives you the report to send another way.

## See the reports saved in Starboard

1. Go to **Settings**, then **General**.
2. Under **Testing**, the saved reports are listed, newest first. Open **The full report** to read one.
3. Select **Mark fixed** when it is dealt with, or **More actions**, then **Remove**, to delete it.
4. Select **Download all** to save every report as one file.

## Things to note

- A report never holds your password, your API keys, cookies or anything typed into the page's fields. Email
  addresses, long numbers and keys are replaced. The page title and the text on the page are copied as they are,
  so check the report before you send it.
- Reports saved in Starboard are kept on the server in `data/ux-notes.json`, which only Starboard's user can
  read. They are in Starboard's backups.
- The button loads only while **Send feedback** is active, so it costs nothing when it is not.
- Notes from the older **Note an issue** button are kept and listed with the new reports.

## If it does not work

- **No Send feedback button:** check that **Send feedback** is active, then reload the page.
- **Save in Starboard says it is not sent:** you were signed out. Sign in again, then send it again.
  The report is kept until you close the window, so you can also select **Back** and copy it instead.
- **Open in GitHub does nothing:** your browser may have blocked the new window. Allow pop-ups for Starboard, or
  copy the report and paste it into a new issue.

## Find out more

- [Read the log and report a problem](read-the-log.md)
- [Snaglist's help: send feedback on a site](https://github.com/TheMightyTRex/snaglist/blob/main/docs/guides/send-feedback-on-a-site.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
