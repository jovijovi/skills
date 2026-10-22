---
name: decide-with-me
description: Discuss open choices with the user through short rounds of multiple-choice questions, then confirm a plan before acting. Use when the user asks to talk something through, compare options or decide interactively (for example "let's discuss", "help me decide", "interactive Q&A", "交互式问答", "讨论一下", "帮我决定"). Also use it first, before any build or design skill, when an open-ended request such as "build me a blog", "set up CI" or "帮我做一个个人博客" leaves key choices open (stack, scope, design, hosting, naming) and a wrong guess would be costly to undo. Not for facts you can look up, or when the user asked you to choose.
---

# Decide With Me

Turn open questions into decisions the user actually made. You research, frame the options and recommend one; the user chooses; nothing is built until the user confirms the summary. Ask only what would change the result, in as few words as possible.

## When to use

- The user asks for a discussion, an interactive Q&A or help deciding.
- An open-ended request ("build me a blog", "set up CI", "redesign this page") leaves choices that only the user can make (stack, scope, design, hosting, cost, naming, anything irreversible), and a wrong guess would be costly to undo. Settle these before you follow any other skill, such as a design or build skill.

Skip it for facts you can look up, trivial choices with an obvious default, choices the user left to you, and decisions already made.

## The loop

1. **Ground yourself.** Read the code, docs, data and environment first. Never ask for a fact you can check.
2. **Map the decisions as a tree.** Ask first the decisions whose answers determine which others matter. Skip any question that an earlier answer made irrelevant. Group the rest into rounds of at most four questions.
3. **Ask one round** (see [Asking](#asking)) and wait for the reply.
4. **Handle the answers** (see [Handling answers](#handling-answers)) and state in one line what is now decided.
5. **Repeat** until every decision that changes the result is made.
6. **Pass the [confirmation gate](#confirmation-gate).**
7. **Offer a [decision record](#decision-record).**
8. **Act** only within what was confirmed.

## Writing questions

- One decision per question, in the user's language and the user's own words for things. Define a term in one line the first time it matters, and use the same name for the same thing in every round.
- Two to four options that do not overlap, each labeled in a few words. Put your recommended option first and mark it in the user's language, for example "(Recommended)" or "（推荐）".
- Describe each option by its consequence: if it is chosen, what happens and what it costs (effort, money, risk, reversibility). Use names, numbers and examples.
- Give the reason for a recommendation as cause and effect: "because …, so …". If you have no preference, say so.
- When one choice rules out or constrains another, say so in the option.
- Use multi-select only for independent options.
- For layout, interface, structure or wording choices, attach a small text sketch or example to each option.
- Mark uncertainty; never present a guess as a fact. The user can always answer in their own words.

## Asking

**With a structured question tool** (for example `AskUserQuestion` in Claude Code), use one call per round: up to four questions, each with a short header, options with descriptions, and previews for visual choices.

**Without one**, write the round as normal Markdown, not inside a code block. Number every question, letter every option and end with the reply hint, even for a single question. Write all of it, including the recommendation mark and the reply hint, in the user's language. Keep the numbers and letters even if your usual style prefers plain bullets, because the user replies with them:

```markdown
**Q1 · <short header>**: <question>
- **a)** <option> (Recommended) — <what happens / main trade-off>
- **b)** <option> — <what happens / main trade-off>

Reply like `1a 2b`, or answer in your own words.
```

For example:

**Q1 · Hosting**: Where should the blog run?
- **a)** GitHub Pages (Recommended) — free for public repositories, and it rebuilds on every push
- **b)** Your own server — full control; you maintain TLS, backups and updates

Reply like `1a`, or answer in your own words.

Put at most two sentences of context before a round. After it, end your turn: no summary, no provisional plan, and no mention of clicking unless you used a question tool.

## Handling answers

Read every answer literally; a free-text reply may change the plan. Never silently replace the user's choice with your own.

| When the user… | Do this |
|---|---|
| picks an option | Record it and move on. |
| answers in their own words | Follow what it says. It may add a constraint or reject every option. |
| says "no preference" or "you decide" | Take your recommendation and say so. |
| does not understand | Ask again in different words, with a concrete scenario or a before/after example. |
| replies with a question | Answer it briefly, then ask again whatever is still open. |
| adds a requirement | Fold it into the plan and ask the follow-up questions it raises. |
| changes an earlier answer | Update it and recheck the decisions that depend on it. |
| redirects you in the middle of work | Stop, reconcile it with earlier decisions, and confirm before you continue. |

If new information undermines one of your recommendations, say so and ask again.

## Confirmation gate

Before any work, show every decision in one line each, the defaults you filled in (marked as yours), what you will do in order, and the costs, risks and anything outward-facing or irreversible. Then ask for an explicit go-ahead, for example "Start (Recommended)" or "Adjust first". A yes covers only that plan. A new outward-facing or irreversible step needs its own confirmation.

## Decision record

At the end, ask whether to save a record. If the user agrees, ask where (suggest `docs/decisions/YYYY-MM-DD-<topic>.md`) and fill in [the template](references/decision-record-template.md). If you cannot write files, put the record in the conversation.
