---
name: superpowers
description: |
  Hyper-Extract agentic superpowers for implementing plans and managing complex work.
  Use when a plan or design doc exists and you need help executing it.
  Available sub-skills: superpowers:subagent-driven-development, superpowers:executing-plans.
license: MIT
compatibility: Plans written in Markdown with checkbox task syntax.
metadata:
  author: Hyper-Extract
  version: "1.0"
---

# Superpowers

Agentic execution helpers for Hyper-Extract plans.

## Available Skills

| Skill | When to use |
|-------|-------------|
| `superpowers:subagent-driven-development` | Large or cross-cutting tasks; delegate to focused subagents. |
| `superpowers:executing-plans` | Small, sequential tasks; execute directly in this session. |

## How to invoke

If the current plan is in `docs/superpowers/plans/<name>.md` or `openspec/changes/<name>/tasks.md`, choose one of the sub-skills based on task size and execute the unchecked tasks.

## Plan format

Plans should contain checkbox tasks:

```markdown
- [ ] Task 1: do something
- [ ] Task 2: run tests
- [ ] Task 3: update docs
```

Skills will read the plan, execute tasks, and update checkbox state.
