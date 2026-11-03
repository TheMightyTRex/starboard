# How this help is written

For anyone adding to or changing the help centre. Every article belongs to one of three tiers, follows the
writing rules below and is listed in the [help centre home](README.md).

## The three tiers

| Tier | Folder | What it is | Answers |
|---|---|---|---|
| 1 | `topics/` | A topic: one task, one question, one article | "How do I do this one thing?" |
| 2 | `guides/` | A guide: an ordered journey made of topics | "How do I get from nothing to this outcome?" |
| 3 | `basics/` | The basics: an idea explained from the start | "What is this, and why does it matter?" |

- **A topic covers one task.** A second task is a second topic, and the two link to each other.
- **A guide is mostly links.** Each step is one or two sentences and a link to the topic that holds the
  instructions. A guide never repeats a topic's steps, so each instruction is kept in one place. If a step
  has no topic, write the topic first.
- **Basics teach, topics and guides direct.** If a topic needs to explain what Docker is before it can give
  the steps, link to the basics article instead.

Readers may know very little about computers. Write so that someone who has never opened a terminal can
follow every step, and link to the basics for anything they might not know.

## Topic layout (Tier 1)

```
[Help centre](../README.md) · <Area>

# <The task, in the reader's words, starting with a verb>

One or two sentences: what this does and what you will have at the end. The answer comes first.

## Before you begin          (omit when there is nothing)
- What must be true or to hand, each with a link to the topic that sets it up.

## Steps
1. One action per step, with the on-screen label in bold: Select **Add an app**.
2. Commands in a fenced `bash` block of their own, one command per block.
3. Say what happens after a step when it is not obvious: "Starboard shows the setup code."

## Things to note             (omit when there is nothing)
## If it does not work         (omit when there is nothing)
## Find out more
- Links to related topics, guides and basics.
```

Use exactly one of these as the topic's kind, on the line under the title after the area: how-to,
reference or troubleshooting.

## Guide layout (Tier 2)

```
[Help centre](../README.md) · Guides

# <The outcome, in the reader's words>

Who this is for, what you will have at the end, and about how long it takes.

## Before you begin
## The steps at a glance       (a numbered list, then a Mermaid flowchart of the same steps)
## Step 1: <short name>        (one or two sentences, the link to the topic, and how you know it worked)
## What next
```

## Basics layout (Tier 3)

```
[Help centre](../README.md) · The basics

# <What X is>

The idea in two or three sentences, with an everyday comparison where one helps.

## <A few short sections that build the idea up>
## What this means for Starboard
## Find out more
```

## Writing rules

1. **British English**, sentence case for every heading and title.
2. **No em dashes and no contractions.** Use a comma, a colon or a new sentence. "do not", "cannot", "it is".
3. **Select, not click or tap.** "Select **Save app**." For pages: "Go to **Settings**, then **Manage apps**."
4. **No positions.** Never "top right", "on the left" or "scroll down": name the control.
5. **Page, not screen. Switches are on and off**, never enable, disable or toggle.
6. **On-screen labels are copied exactly** and shown in bold inside steps. If a label is wrong, fix the
   label in Starboard, not the help.
7. **Sentences under 25 words, paragraphs of two to four sentences.** Active voice, present tense, "you".
8. **Expand an abbreviation the first time in each article:** "VPN (virtual private network)". Common ones
   need no expansion: URL, API.
9. **Numbers:** one to nine in sentences, numerals for 10 and above, always numerals for sizes, ports, steps
   and times: "port 8095", "512 MB", "Step 2".
10. **Links name their destination:** "Read [Add an app](add-an-app.md)", never "click here".
11. **No exclamation marks and no emoji.** Calm and plain: every problem comes with a next step.
12. **Describe in words anything a picture shows,** so screen readers and search can use it.
13. **Commands are copied, not typed.** Put each command in its own `bash` block, and say what it does in
    the sentence before it. Mark anything the reader must change, such as `<your server>`, and say what to
    put there.
14. **Made-up examples only:** addresses such as `192.168.1.20`, names such as Sam and Alex. Never a real
    address, key or name.
