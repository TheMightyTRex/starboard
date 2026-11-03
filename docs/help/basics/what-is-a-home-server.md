[Help centre](../README.md) · The basics

# What a home server is

A home server is a computer in your home that stays powered on and does jobs for everyone in the house, such
as storing and playing films, series, music and books. It is like a pantry: everything is kept in one place,
and anyone in the house can fetch what they want from it.

## A computer that serves others

Most computers are used by one person sitting in front of them. A server is different: other devices ask it
for things over your home network. Your television asks it for a film, your phone asks it for an audiobook, and
your laptop asks it what is downloading.

The word "server" sounds grand, but any computer can be one. It only needs to stay powered on and stay connected.

## What can be a home server

- **An old laptop or desktop computer.** A laptop has a built-in battery, which helps if the power drops for a
  moment.
- **A small, quiet "mini PC".** These use little electricity and fit on a shelf.
- **A Raspberry Pi.** A credit-card-sized computer that costs little to run. Read
  [Install Starboard on a Raspberry Pi](../guides/install-on-a-raspberry-pi.md).
- **A NAS (network-attached storage) box.** A box made to hold several drives.

How big it needs to be depends on what you run. For Starboard itself, read
[What you need to run Starboard](../topics/what-you-need.md).

## Why most home servers run Linux

Linux is a free operating system, like Windows or macOS. Most home servers use it because it is free, runs well
on older or smaller computers, and is what most media apps are built for. Ubuntu, Linux Mint, Debian, Fedora and
Raspberry Pi OS are all kinds of Linux.

You do not need to know Linux well. You mostly use it by typing a few commands, which
[The terminal: typing commands](the-terminal.md) explains.

## Apps on the server

A home server runs apps that each do one job: one plays your media, one finds new episodes, one downloads. Each
app has a web page that you open in a browser on any device at home.

Most people run these apps with Docker, which keeps each one in its own sealed box. Read
[What Docker is](what-is-docker.md).

## With or without a monitor

A server does not need its own monitor or keyboard. Many people set it up once and then control it from another
computer, by opening its web pages or by connecting with SSH (secure shell). Read
[Connect to your server from another computer](../topics/connect-with-ssh.md).

## What this means for Starboard

Starboard runs on your home server, next to your other apps. You open it from any phone or computer at home, and
it shows you what every app on the server is doing.

## Find out more

- [What Starboard is](what-is-starboard.md)
- [Addresses and ports](addresses-and-ports.md)
- [The apps Starboard works with](the-apps.md)
- [Build a media server from nothing](../guides/build-a-media-server-from-nothing.md)
