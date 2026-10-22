---
name: decide-with-me
description: Discuss open choices with the user through short rounds of multiple-choice questions, then confirm a plan before acting. Use when the user asks to talk something through, compare options or decide interactively (for example "let's discuss", "help me decide", "interactive Q&A", "交互式问答", "讨论一下", "帮我决定"). Also use it first, before any build or design skill, when an open-ended request such as "build me a blog", "set up CI" or "帮我做一个个人博客" leaves key choices open (stack, scope, design, hosting, naming) and a wrong guess would be costly to undo. Not for facts you can look up, or when the user asked you to choose.
---

# Decide With Me

Turn open questions into decisions the user actually made. You do the research, frame the options and recommend one. The user chooses. Nothing is built until the user confirms the summary.

## When to use

Use this skill when:

- the user asks for a discussion, an interactive Q&A or help deciding;
- an open-ended request ("build me a blog", "set up CI", "redesign this page") leaves choices that only the user can make (stack, scope, design, hosting, cost, naming, anything irreversible), and a wrong guess would be costly to undo.

When another skill also applies, for example a design or build skill, settle the open choices with this skill first and then follow the other skill with those decisions.

Do not use it for facts you can look up, for trivial choices with an obvious default, when the user asked you to choose, or to reopen something the user has already decided.

## The loop

1. **Ground yourself first.** Read the code, docs, data and environment. Never ask the user for a fact you can check yourself.
2. **List the open decisions.** Order them so that earlier answers inform later ones. Group related decisions into rounds of at most four questions.
3. **Ask one round** (see [Asking](#asking)), then stop and wait for the reply.
4. **Handle the answers** (see [Handling answers](#handling-answers)) and state briefly what is now decided.
5. **Repeat** until every decision that matters is made.
6. **Summarize and ask for a go-ahead** (see [Confirmation gate](#confirmation-gate)).
7. **Offer a decision record** (see [Decision record](#decision-record)).
8. **Act** only within what was confirmed.

## Writing questions

- One decision per question, phrased as a question in the user's language.
- Two to four options that do not overlap. Put your recommended option first and mark it, for example "(Recommended)" or "（推荐）".
- Give each option a one-line description: what happens if it is chosen and its main trade-off (effort, cost, risk, reversibility). Concrete beats abstract: use names, numbers and examples.
- Recommend only with a reason. If you have no preference, say so instead of inventing one.
- Use multi-select only when the options are independent of each other.
- For layout, interface, structure or wording choices, attach a small text sketch or example to each option so the user can compare them side by side.
- The user can always answer in their own words. Never force a choice from the list.
- Mark uncertainty. Do not present a guess as a fact.

## Asking

**If the host offers a structured question tool** (for example `AskUserQuestion` in Claude Code), use it: one call per round, up to four questions, each with a short header, options with descriptions, and previews for visual choices.

**Otherwise, write the round in this Markdown format**, as normal text rather than inside a code block. Number every question, letter every option, and end with the reply hint, even when there is only one question:

```markdown
**Q1 · <short header>**: <question>
- **a)** <option> (Recommended) — <what happens / main trade-off>
- **b)** <option> — <what happens / main trade-off>

**Q2 · <short header>**: <question>
- **a)** <option> (Recommended) — ...
- **b)** <option> — ...

Reply like `1a 2b`, or answer in your own words.
```

Keep the question numbers and option letters even if your usual style prefers plain bullets: the user replies with them. A round with one question looks like this:

**Q1 · Hosting**: Where should the blog run?
- **a)** GitHub Pages (Recommended) — free, and it rebuilds on every push; the repository must be public
- **b)** Your own server — full control; you maintain TLS, backups and updates

Reply like `1a`, or answer in your own words.

Then end your turn so the user can reply; do not add a summary or a provisional plan after the questions. Do not tell the user they can click or select anything unless you used a question tool.

Put at most one or two sentences of context before a round.

## Handling answers

Read every answer literally. A free-text reply may change the plan.

| When the user… | Do this |
|---|---|
| picks an option | Record it and move on. |
| answers in their own words | Follow what it actually says. It may add a constraint or reject every option. |
| says "no preference" or "you decide" | Take your recommendation and say that you did. |
| says they do not understand | Ask the same decision again in different words, with a concrete scenario or a before/after example. Do not repeat the original wording. |
| replies with a question | Answer it briefly and factually first, then ask again whatever is still open. |
| adds a requirement | Acknowledge it, fold it into the plan and ask the follow-up questions it raises. |
| changes an earlier answer | Update it and recheck the decisions that depended on it. |
| redirects you in the middle of work | Stop, reconcile the new direction with earlier decisions, and confirm before you continue. |

If new information undermines one of your recommendations, say so and ask again.

## Confirmation gate

Before doing any work, show:

- every decision, one line each;
- the defaults you filled in yourself, marked as yours;
- what you will do, in order;
- costs, risks and anything outward-facing or irreversible.

Then ask for an explicit go-ahead, for example "Start (Recommended)" or "Adjust first". Do not act before a clear yes. A yes covers only the summarized plan. A new outward-facing or irreversible step that comes up later needs its own confirmation.

## Decision record

At the end, ask whether to save a record of the discussion. If the user agrees, ask where to put it and suggest a path such as `docs/decisions/YYYY-MM-DD-<topic>.md`. Fill in [the decision record template](references/decision-record-template.md). If you cannot write files, put the record in the conversation instead.

## Style

- Use the user's language. Keep option labels to a few words.
- Ask one round per message, with no lecture between rounds.
- Never ask more than four questions in one round.

## Avoid

- Open-ended "what do you want?" questions without options.
- Asking for facts you could have found yourself.
- Overlapping options, or a recommended option without a reason.
- Acting on partial answers or before the go-ahead.
- Silently replacing the user's choice with your own preference.
