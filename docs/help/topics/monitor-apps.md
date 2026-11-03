[Help centre](../README.md) · Your server · how-to

# Find out what each app is using

The Monitor page shows, live, how hard your server is working: its processor, memory, temperature, network and
disks. With one install option on, it also lists how much processor and memory each app is using.

## Before you begin

- To see each app's use, answer Yes to **Show each app's processor and memory use?** when you run
  `./install.sh`. Run it again at any time to change your answer. Read
  [Change what Starboard can access](change-what-starboard-can-access.md).
- Without that option, Monitor shows the whole server only.

## Steps

1. Go to **System**, then **Monitor**. The charts start after a few seconds and show the last 3 minutes.
2. Read the charts: **Processor**, **Memory**, **Processor temperature**, **Network** and **Disk activity**.
3. Find **Apps**. It lists the 12 busiest apps, with each one's **Processor** and **Memory**.
4. Optional: select **Pause** to hold the charts still while you read them. Select **Pause** again to carry on.

## Things to note

- Monitor reads the server only while the page is open and in view. Nothing runs when you close it.
- It reads every 2 seconds unless you change it. To read less often, go to **Settings**, then **Performance**,
  and change **Monitor page readings**.
- With Docker access as well, the **Apps** list shows each app's name. Without it, it shows a short ID for each
  app instead. Read [Update your apps](update-your-apps.md) for what Docker access does.
- **Processor threads** shows how busy each part of the processor is.
- **Processor temperature** appears only when the server reports one.
- To see how much Starboard itself uses, go to **Settings**, then **Performance**, and read **Starboard now**.

## If it does not work

- **No Apps list:** the per-app option is inactive. Run `./install.sh` again and answer Yes to **Show each app's
  processor and memory use?**
- **The installer says per-app use stays inactive:** this computer does not support it, so Monitor shows the whole
  server only.
- **Could not read the server:** Starboard could not take a reading. Select **Pause** twice to try again, or
  reload the page.

## Find out more

- [Make Starboard use less of your server](make-starboard-lighter.md)
- [Check free space and what is using it](check-storage.md)
- [Change what Starboard can access](change-what-starboard-can-access.md)
- [What Docker is](../basics/what-is-docker.md)
