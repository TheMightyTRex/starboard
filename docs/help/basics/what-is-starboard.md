[Help centre](../README.md) · The basics

# What Starboard is

Starboard is a dashboard for a home media server: one page that shows all your media apps, whether each one is
working, and what they are doing. Think of it as the front desk of a hotel. Behind it, many rooms are busy, but
you only need to visit the desk to see what is going on and to ask for something.

## The problem it solves

A home media server usually runs several apps. One finds series, another finds films, another downloads, and
another plays everything on your television. Each app has its own web page, its own address and its own
settings.

Without a dashboard, you have to remember every address and open each app in turn to check on it. Starboard
puts them all in one place, behind one password.

## What you can do with it

- **See every app at a glance.** The **Apps** page shows each app. In the standard design, apps that are not
  responding come first, so problems are easy to spot.
- **Search once, add anywhere.** **Search** looks in Sonarr, Radarr, Lidarr and Readarr at the same time and adds
  what you choose to the right app.
- **Follow downloads.** **Downloads** lists what is downloading, and can pause and resume it.
- **See what is coming up.** **Coming up** lists new episodes, films and albums due soon, as a list or a calendar.
- **Check the server.** **System** shows free space, disk health, what each app is using and the log.
- **Get alerts.** Starboard can send you a message when an app stops answering or a disk gets full.

If these app names are new to you, read [The apps Starboard works with](the-apps.md).

## Light on your server

Starboard is built for smaller servers, such as a Raspberry Pi or an old laptop. It uses about 16 MB of memory
while it is idle, and very little of the processor, so your server's power goes to your apps.

Nothing runs in the background unless you activate it. **Settings**, then **Performance**, shows what Starboard
uses and lets you deactivate each piece of background work.

## Safe by default

Starboard asks before it is given any access to your computer, and every kind of access is optional. One
password protects it. Your API keys stay on the server and are never sent to your browser.

By default, only phones and computers on your home network can open it. To use it away from home, there are
safe ways to do so, explained in [Use Starboard away from home safely](../guides/use-starboard-away-from-home.md).

## What this means for Starboard

Starboard does not replace your media apps. It sits in front of them and talks to each one, using the address
and API key you give it. If you do not have any media apps yet, Starboard can help you install them.

## Find out more

- [What a home server is](what-is-a-home-server.md)
- [The apps Starboard works with](the-apps.md)
- [What you need to run Starboard](../topics/what-you-need.md)
- [Install Starboard on a Linux computer](../guides/install-on-a-linux-computer.md)
- [Build a media server from nothing](../guides/build-a-media-server-from-nothing.md)
