---
name: superpowers-subagent-driven-development
description: |
  Implement a written plan task-by-task by delegating focused work to subagents.
  Use when a plan document (e.g., docs/superpowers/plans/*.md or openspec tasks.md)
  contains checkbox tasks that should be executed independently.
  Preferred over superpowers:executing-plans when tasks are large, cross-cutting,
  or benefit from isolated context.
license: MIT
compatibility: Requires Kimi Code CLI Agent tool.
metadata:
  author: Hyper-Extract
  version: "1.0"
---

# Subagent-Driven Development

Implement a plan by spawning focused subagents for each task.

## When to use

- A plan or tasks artifact lists concrete checkbox steps.
- Tasks touch multiple files or require deep investigation.
- You want isolated context per task to avoid context-window bloat.

## Workflow

1. **Read the plan**
   - Open the plan file (e.g., `docs/superpowers/plans/<name>.md` or `openspec/changes/<name>/tasks.md`).
   - Identify all unchecked tasks (`- [ ]`).

2. **Summarize remaining work**
   - List tasks in dependency order.
   - Note any files, tests, or commits mentioned by the plan.

3. **Create a todo list**
   - Use `SetTodoList` to track each task.

4. **Execute tasks with subagents**
   - For each task, start a `coder` subagent with a focused prompt.
   - Include:
     - The task description from the plan.
     - Relevant file paths and constraints.
     - Expected test or verification steps.
     - Whether the subagent should commit or only modify files.
   - Prefer foreground subagents so you can review output before continuing.

5. **Verify after each task**
   - Run tests or checks specified by the plan.
   - Update the todo list.

6. **Mark plan progress**
   - Update the checkbox state in the plan file as tasks complete.
   - Do not rewrite plan intent; only mark `- [ ]` → `- [x]`.

7. **Final summary**
   - Report completed tasks, files changed, and any blockers.

## Subagent Prompt Template

```markdown
Task: <task name>

Context:
- Project root: /Users/parkermeng/Documents/github/Hyper-Extract
- Plan file: <path>
- Goal: <one-sentence summary>

Instructions:
1. Read <relevant files>.
2. Implement <specific change>.
3. Run <verification command>.
4. Do NOT modify unrelated files or tests unless instructed.
5. Return a concise summary of changes and test results.
```

## Guardrails

- Do not spawn a subagent for trivial one-line changes; do those directly.
- If a task is blocked, report it and ask the user before proceeding.
- Keep plan files as the source of truth; subagents should not rewrite them.
