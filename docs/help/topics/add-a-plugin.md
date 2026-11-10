[Help centre](../README.md) · Plug-ins · how-to

# Add a plug-in

Add a plug-in to give Starboard something new, such as Live TV or more styles to choose from. Starboard shows
what the plug-in may do and tests it before anything is added. At the end, the plug-in is active and what it adds
is ready to use.

## Before you begin

- For a plug-in that is not built into Starboard, you have its manifest address, its `starboard-plugin.json`
  file, or its installer. Plug-ins you can add are listed in [The plug-in collection](../basics/plugin-collection.md).
- You know your Starboard password. Adding and removing a plug-in ask for it.
- To understand what a plug-in can and cannot do first, read
  [What a plug-in can change](../basics/what-plugins-can-change.md).

## Steps

1. Go to **Settings**, then **Plug-ins**.
2. Under **Add a plug-in**, in **The plug-in's manifest address**, paste the address the plug-in's page gives.
   If you have the file instead, choose it in **Or its manifest file**.
3. Select **See what it does**. Starboard shows the plug-in's name, **What it may do** with a risk level for each
   permission, and **Test results**.

   ![Settings, Plug-ins, with the manifest address (step 2), See what it does (step 3) and the test results outlined](../images/add-a-plugin-1-preview.png)

4. Read **What it may do** and **Test results**. A plug-in with errors cannot be added. Enter your Starboard
   password and select **Add**, followed by the plug-in's name, such as **Add Styles**.
5. In the plug-in's own section, select **Activate**. Its status changes to **Active**. To stop it later, select
   **Deactivate**.

   ![The Styles plug-in's section, with its status and Deactivate (step 5) outlined](../images/add-a-plugin-2-active.png)

6. For a plug-in with styles: select **Display** in the header of any page, then choose a style under **Style**.
   The page changes straight away. You can also select **Use this style** in the plug-in's own section. Read
   [Change text size, theme and other display settings](display-and-accessibility.md#choose-a-style-from-a-plug-in).

   ![The Display panel, with the Style list (step 6) outlined](../images/add-a-plugin-3-style.png)

### A plug-in built into Starboard

Some plug-ins, such as Live TV, come with Starboard. They are listed under **Built into Starboard** in
**Settings**, then **Plug-ins**. Select **Add** and the plug-in's name, enter your Starboard password, then select
**Add** and its name again. It is added and active at once. For Live TV, read
[Set up free Live TV in Jellyfin](set-up-live-tv.md).

### With the plug-in's own installer

Some plug-ins, such as Styles, come with an installer. Run it on any computer with Python, such as
`python3 install.py`, and enter your Starboard's address, such as `http://192.168.1.20:8095`. Your browser opens
**Settings**, then **Plug-ins**, with the plug-in already shown at step 3. Carry on from step 4.

## Test a plug-in

If you make plug-ins, test one before you share it. In **Settings**, then **Plug-ins**, under **Test a plug-in**,
choose its `starboard-plugin.json` and select **Test it**. Starboard lists every issue with where it is, what is wrong and
how to fix it. Accessibility is always tested: every style in light and dark, and the words people read.

![Test a plug-in, with a style that fails contrast: the list of issues, each with how to fix it, is outlined](../images/add-a-plugin-4-test.png)

## Things to note

- Styles apply to the browser you choose them in, like the rest of **Display**.
- Some plug-ins add cards to the dashboard. Read [Use and change the dashboard](use-the-dashboard.md).
- **High contrast**, text size, wider spacing, underlined links and reduced motion always win over a style.
- **Remove** and the plug-in's name stops the plug-in and its containers, and stops its key working. Its folder
  is kept in `data/plugins/.removed`, so you decide when to delete it.
- **Deactivate all plug-ins** deactivates every active plug-in at once, if something goes wrong.

## If it does not work

- **"This plug-in cannot be added":** read the test results under it. The plug-in's maker needs to fix each error.
- **"Starboard has no access to Docker here":** plug-ins that run containers need Docker access. Read
  [Change what Starboard can access](change-what-starboard-can-access.md). Plug-ins with only styles do not.
- **A style does not change anything:** check that **High contrast** is inactive in **Display**, and that the
  plug-in is **Active**.

## Find out more

- [Write a plug-in](../basics/write-a-plugin.md)
- [What a plug-in can change](../basics/what-plugins-can-change.md)
- [The plug-in collection](../basics/plugin-collection.md)
- [How Starboard keeps your server safe](../basics/how-starboard-keeps-you-safe.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
