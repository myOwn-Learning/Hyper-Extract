---
name: openspec
description: |
  OpenSpec change-management workflow entry point for Hyper-Extract.
  Use when the user wants to propose, explore, apply, or archive an OpenSpec change.
  Delegates to the openspec-* sub-skills.
license: MIT
compatibility: Requires openspec CLI and an openspec/ directory.
metadata:
  author: Hyper-Extract
  version: "1.0"
---

# OpenSpec

Manage Hyper-Extract changes using the OpenSpec workflow.

## Available Skills

| Skill | When to use |
|-------|-------------|
| `openspec:explore` | Think through a problem or clarify requirements before proposing a change. |
| `openspec:propose` | Create a new change with proposal, design, and tasks artifacts. |
| `openspec:apply-change` | Implement an approved change task-by-task. |
| `openspec:archive-change` | Finalize and archive a completed change. |

## Typical Workflow

1. **Explore** — clarify the problem and scope.
2. **Propose** — generate the change artifacts.
3. **Apply** — implement the tasks.
4. **Archive** — finalize the change.

## Configuration

Project-level OpenSpec config lives in `openspec/config.yaml`.
Changes are stored under `openspec/changes/<change-name>/`.

Use the specific sub-skill that matches the current phase rather than this entry skill.
