---
name: planning-with-files
description: Implements Manus-style file-based planning for complex tasks. Creates task_plan.md, findings.md, and progress.md, and maintains human-readable TASK_PROGRESS.md updates. Use when starting complex multi-step tasks, research projects, or any task requiring >5 tool calls.
---

# Planning with Files

Work like Manus: Use persistent markdown files as your "working memory on disk."

## Important: Where Files Go

- **Templates** are in this skill's `templates/` folder
- **Your planning files** go in **your project directory**

| Location | What Goes There |
|----------|-----------------|
| Skill directory | Templates, scripts, reference docs |
| Your project directory | `task_plan.md`, `findings.md`, `progress.md` |

## Quick Start

Before ANY complex task:

> **Note:** Run helper scripts with `sh` or `bash` to avoid execute-permission issues.

1. **Clear or create `TASK_PROGRESS.md`** — Reset file for the new user request
2. **Create `task_plan.md`** — Use [templates/task_plan.md](templates/task_plan.md) as reference
3. **Create `findings.md`** — Use [templates/findings.md](templates/findings.md) as reference
4. **Create `progress.md`** — Use [templates/progress.md](templates/progress.md) as reference
5. **Re-read plan before decisions** — Refreshes goals in attention window
6. **Update after each phase** — Mark complete, log errors

> **Note:** Planning files go in your project root, not the skill installation folder.

## TASK_PROGRESS.md Output (Human-Readable Only)

- **Location:** Project root.
- **Reset rule:** Before creating a new task plan for each user request, clear or create `TASK_PROGRESS.md`.
- **When to write:** Append a plain-language summary of the task plan (goal and main steps) when a plan is created, during progress updates, and on completion or exception.
- **Language:** Use the current user request language. If mixed, use the dominant language. If undetectable, use English.
- **Audience:** Non-technical users in AIGC design contexts; clear and plain wording.
- **Content limits:** Do not include commands, tools/skills, environment variables, secrets, file paths, code, or technical error causes.
- **Errors:** If an exception happens, write that an internal error occurred without details. If the error occurred before any progress entry, attempt to write the error summary again.
- **Subtasks:** If there are multiple subtasks, you may say "item N of M" in natural language.
- **Format:** Markdown file, and content must be natural language only (no technical details).
- **Task plan sync:** When a new `task_plan.md` is created, append a markdown summary of the task goal and the main phases in the user's language.
- **Findings sync:** When `findings.md` is updated, append a markdown summary of the new findings in the user's language.
- **Detail level:** Provide fuller progress context (what is done, what is in progress, what is next) while staying non-technical.
- **Completion tone:** When marking a task as complete in `TASK_PROGRESS.md`, append 1-2 celebratory emojis.

## The Core Pattern

```
Context Window = RAM (volatile, limited)
Filesystem = Disk (persistent, unlimited)

→ Anything important gets written to disk.
```

## File Purposes

| File | Purpose | When to Update |
|------|---------|----------------|
| `task_plan.md` | Phases, progress, decisions | After each phase |
| `findings.md` | Research, discoveries | After ANY discovery |
| `progress.md` | Session log, test results | Throughout session |

## Critical Rules

### 0. Reset TASK_PROGRESS.md Per Request
Before creating a new plan, clear or create `TASK_PROGRESS.md` for the current user request.

### 0.1 Sync Plan and Findings
When `task_plan.md` or `findings.md` changes, append a clear, markdown-formatted, non-technical summary to `TASK_PROGRESS.md` in the user's language.

### 1. Create Plan First
Never start a complex task without `task_plan.md`. Non-negotiable.

### 2. The 2-Action Rule
> "After every 2 view/browser/search operations, IMMEDIATELY save key findings to text files."

This prevents visual/multimodal information from being lost.

### 3. Read Before Decide
Before major decisions, read the plan file. This keeps goals in your attention window.

### 4. Update After Act
After completing any phase:
- Mark phase status: `in_progress` → `complete`
- Log any errors encountered
- Note files created/modified

### 5. Log ALL Errors
Every error goes in the plan file. This builds knowledge and prevents repetition.

```markdown
## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| FileNotFoundError | 1 | Created default config |
| API timeout | 2 | Added retry logic |
```

### 6. Never Repeat Failures
```
if action_failed:
    next_action != same_action
```
Track what you tried. Mutate the approach.

## The 3-Strike Error Protocol

```
ATTEMPT 1: Diagnose & Fix
  → Read error carefully
  → Identify root cause
  → Apply targeted fix

ATTEMPT 2: Alternative Approach
  → Same error? Try different method
  → Different tool? Different library?
  → NEVER repeat exact same failing action

ATTEMPT 3: Broader Rethink
  → Question assumptions
  → Search for solutions
  → Consider updating the plan

AFTER 3 FAILURES: Escalate to User
  → Explain what you tried
  → Share the specific error
  → Ask for guidance
```

## Read vs Write Decision Matrix

| Situation | Action | Reason |
|-----------|--------|--------|
| Just wrote a file | DON'T read | Content still in context |
| Viewed image/PDF | Write findings NOW | Multimodal → text before lost |
| Browser returned data | Write to file | Screenshots don't persist |
| Starting new phase | Read plan/findings | Re-orient if context stale |
| Error occurred | Read relevant file | Need current state to fix |
| Resuming after gap | Read all planning files | Recover state |

## The 5-Question Reboot Test

If you can answer these, your context management is solid:

| Question | Answer Source |
|----------|---------------|
| Where am I? | Current phase in task_plan.md |
| Where am I going? | Remaining phases |
| What's the goal? | Goal statement in plan |
| What have I learned? | findings.md |
| What have I done? | progress.md |

## When to Use This Pattern

**Use for:**
- Multi-step tasks (3+ steps)
- Research tasks
- Building/creating projects
- Tasks spanning many tool calls
- Anything requiring organization

**Skip for:**
- Simple questions
- Single-file edits
- Quick lookups

## Templates

Copy these templates to start:

- [templates/task_plan.md](templates/task_plan.md) — Phase tracking
- [templates/findings.md](templates/findings.md) — Research storage
- [templates/progress.md](templates/progress.md) — Session logging

## Scripts

Helper scripts for automation:

- `scripts/init-session.sh` — Initialize all planning files (run with `sh`/`bash`)
- `scripts/check-complete.sh` — Verify all phases complete (run with `sh`/`bash`)

Examples:

```bash
sh scripts/init-session.sh
```

```bash
bash scripts/check-complete.sh
```

## Advanced Topics

- **Manus Principles:** See [references/reference.md](references/reference.md)
- **Real Examples:** See [references/examples.md](references/examples.md)

## Anti-Patterns

| Don't | Do Instead |
|-------|------------|
| Use TodoWrite for persistence | Create task_plan.md file |
| State goals once and forget | Re-read plan before decisions |
| Hide errors and retry silently | Log errors to plan file |
| Stuff everything in context | Store large content in files |
| Start executing immediately | Create plan file FIRST |
| Repeat failed actions | Track attempts, mutate approach |
| Create files in skill directory | Create files in your project |
