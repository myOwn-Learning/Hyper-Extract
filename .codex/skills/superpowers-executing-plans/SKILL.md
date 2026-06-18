---
name: superpowers-executing-plans
description: |
  Execute a written plan task-by-task directly in the current session.
  Use when tasks are small, sequential, and faster to do inline than to delegate.
  Alternative to superpowers:subagent-driven-development for straightforward plans.
license: MIT
compatibility: Any plan with checkbox task lists.
metadata:
  author: Hyper-Extract
  version: "1.0"
---

# Executing Plans

Execute a plan step-by-step in the current session.

## When to use

- A plan file lists concrete checkbox steps.
- Tasks are small and fit comfortably in the current context window.
- You can run tests and verify each step inline.

## Workflow

1. **Read the plan**
   - Open the plan file (e.g., `docs/superpowers/plans/<name>.md` or `openspec/changes/<name>/tasks.md`).
   - Identify all unchecked tasks (`- [ ]`).

2. **Create a todo list**
   - Use `SetTodoList` to track each remaining task.

3. **Execute tasks in order**
   - For each task:
     - Read relevant files.
     - Make the required changes with tools.
     - Run tests or verification commands.
     - Mark the task done in the todo list.

4. **Update the plan file**
   - Change `- [ ]` to `- [x]` for completed tasks.
   - Do not rewrite plan content beyond checkbox state.

5. **Final summary**
   - Report completed tasks, files changed, tests run, and any blockers.

## Guardrails

- If a task grows too large, consider switching to `superpowers:subagent-driven-development`.
- Do not skip verification steps listed in the plan.
- Keep commits atomic per task when the plan specifies commit commands.
