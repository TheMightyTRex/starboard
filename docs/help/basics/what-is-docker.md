[Help centre](../README.md) · The basics

# What Docker is

Docker is a program that runs apps in sealed boxes called containers. Each box holds one app and everything it
needs, and keeps it apart from the rest of the computer. It is like a lunchbox: everything for the meal is packed
inside, it does not spill into the bag, and you can take it out and swap it without touching anything else.

## Why apps come in boxes

An app usually needs other software to run, in exactly the right versions. Two apps on the same computer might
need different versions of the same thing, and installing one can break the other.

Docker solves this. Each app arrives with everything it needs already packed, so it runs the same way on any
computer, and it cannot upset the other apps.

## Images and containers

- **An image** is the packed lunchbox before anyone opens it: a ready-made copy of an app, downloaded from the
  internet. Starboard's ready-made image is called `ghcr.io/themightytrex/starboard`.
- **A container** is an image that is running. You can stop it, start it again or throw it away and make a new
  one from the image. Starboard's container is called `starboard`.

When an app is updated, you download the new image and swap the container for one made from it. Your settings are
kept in a folder outside the box, so they survive the swap.

## Docker Compose

Docker Compose is a part of Docker that starts containers from a written list, called a Compose file. The file
says which image to use, which folders the app may see and how it connects to the network. Starboard's are
`compose.yaml` and `compose.image.yaml`.

With a Compose file, one short command starts everything:

```bash
docker compose up -d
```

`up` means start, and `-d` means "in the background", so you get the prompt back straight away. You do not need to
run this now: the Starboard instructions tell you when.

## Folders the box can see

A container cannot see your files unless you say so. Each folder it may use is listed in the Compose file. Starboard
keeps its settings in a folder called `data`, next to its Compose file. Other folders, such as your media folders,
are only added if you choose to, and Starboard can read them but not change them.

## What this means for Starboard

Starboard runs in a Docker container on your server, next to your media apps. Its box is read-only, runs as your
own user rather than as the administrator, and has no extra powers. Anything more, such as the ability to update
your other apps, is optional and you are asked first.

Starboard uses a Docker setting called host networking, so it can reach your other apps and decide who can connect.
Host networking only works with Docker on Linux, which is why Starboard needs a Linux computer. Read
[Can I use Windows or a Mac?](../topics/windows-and-mac.md)

## Find out more

- [Install Docker](../topics/install-docker.md)
- [Install Starboard with the installer](../topics/install-with-the-installer.md)
- [Install Starboard from the ready-made image](../topics/install-from-the-ready-made-image.md)
- [Change what Starboard can access](../topics/change-what-starboard-can-access.md)
