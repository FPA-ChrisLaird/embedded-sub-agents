# Embedded Subagent Pilot Charter

## Goal

Establish a safe, reusable OpenCode subagent pilot for investigating embedded C/C++ software while preserving the primary engineer's context and decision ownership.

## Context

Embedded firmware investigations commonly require broad repository exploration, build-system tracing, large logs, hardware documentation, and an independent challenge to implementation assumptions. Focused subagents isolate that material from the primary engineering conversation while retaining one accountable decision owner.

## Scope

### In Scope

- Define one global primary agent, `embedded-engineer`, to coordinate focused investigations, integrate evidence, and retain responsibility for decisions and verification.
- Define three global read-only subagents:
  - `embedded-architecture-analyst` for execution contexts, dependencies, state machines, hardware abstraction boundaries, configuration, and resource trade-offs.
  - `embedded-c-quality-reviewer` for correctness, concurrency, timing, integer safety, undefined behavior, and static-analysis evidence.
  - `embedded-build-analyzer` for Makefiles, scripts, toolchains, targets, configurations, artifacts, dependencies, and unsafe commands.
- Configure product-agnostic prompts and permissions that apply across embedded repositories.
- Use `subagent_depth: 1` so only the primary agent may delegate.
- Limit automatic delegation to the three analysis subagents; any future implementation delegation requires approval.
- Constrain each request to at most three non-overlapping subagent investigations.
- Require every subagent hand-off to state scope, evidence, assumptions, risks, and a recommended next action.
- Allow the primary and analysis subagents to run allow-listed, read-only GitHub CLI commands and exact non-mutating Git inspection commands for repository context, issues, pull-request status and diffs, GitHub Actions status and logs, and local repository state. Other primary shell commands require human approval; analysis-subagent shell commands remain denied.
- Pilot the roles against representative embedded-C architecture, quality-review, and Makefile investigation tasks.

### Out Of Scope

- Firmware, build-system, or hardware changes.
- Subagent file edits or local shell command execution. Read-only GitHub CLI retrieval and exact non-mutating Git inspection are in scope.
- Firmware flashing, programming, device I/O, destructive build targets, automated commits, pushes, pull-request comments, or history rewriting. Recognised flashing, programming, clean, package, and release command patterns are hard-denied; any other primary shell command requires human approval.
- Enabling Jira, Confluence, Xray, or other external retrieval integrations for subagents during the initial pilot. Read-only GitHub CLI retrieval is in scope.
- Adding `embedded-c-implementer`, `embedded-test-designer`, `embedded-debugger`, `embedded-hardware-reviewer`, or embedded-specific skills before the pilot demonstrates a recurring need.
- Replacing deterministic C/C++ formatters with an LLM.

## Constraints & Assumptions

- Agent definitions are global OpenCode configuration so they are reusable rather than tied to a product or toolchain.
- The secret-free agent definitions, shared repository-inspection plugin, and depth configuration are version-controlled in this repository as the canonical source, then installed into global OpenCode configuration for reuse across projects.
- Read-only agents may use workspace read, glob, grep, and list operations, plus allow-listed read-only `gh` commands and exact non-mutating Git inspection commands applied by the shared plugin. They must deny edit, task, and all other shell permissions.
- Keep source formatting deterministic through project-selected tooling such as `clang-format` or `uncrustify`.

## Decisions

- The interactive primary agent has no step limit. The architecture analyst and quality reviewer use `steps: 20`; the build analyzer uses `steps: 12`.
- The primary task permission denies by default, then allows only the three analysis roles. Rule order matters because the last matching rule wins.
- The primary agent's prompt, rather than configuration, limits fan-out because OpenCode does not currently provide a fan-out limit.
- `task` permissions restrict automatic model delegation only. Direct user `@` invocation remains possible, so every subagent must enforce its own safety permissions.
- The primary uses approval-gated shell access for a fair end-to-end comparison with Plan and Build. The shared plugin automatically allows only its read-only GitHub and Git inspection commands, hard-denies recognised hazardous command patterns, and requires approval for all other primary shell commands.

## Acceptance Criteria

- Global OpenCode configuration loads successfully after restart.
- `embedded-engineer` is a primary agent and can automatically delegate only to the three defined analysis subagents.
- `subagent_depth` is `1`; every subagent has `permission.task: deny`.
- The three analysis subagents are read-only and cannot edit files, execute local shell commands, or create child subagents. They may use only allow-listed, read-only GitHub CLI and exact Git inspection commands.
- Each analysis agent has the agreed responsibility, model recommendation, iteration limit, and hand-off contract.
- Pilot outputs are concise, evidence-based, and let the primary engineer decide next steps without repeating broad exploration.
- Quality-review hand-offs identify residual risks separately from findings and evidence gaps.
- An exhausted subagent investigation is resumed or its remaining gap is resolved by the primary before the parent task is finalised.
- For changes to persistent or externally encoded representations, the quality reviewer traces every writer and reports unproven ordering dependencies that can persist incompatible data.
- Roles prohibit flashing firmware, programming hardware, device I/O, and destructive build targets. Recognised flashing, programming, clean, package, and release command patterns are hard-denied; other primary shell commands require human approval.

## Verification Plan

- Validate the configuration against the OpenCode schema before saving.
- Restart OpenCode and run `opencode agent list` to confirm the expected agent names, modes, and permissions.
- Delegate one bounded architecture investigation, one quality review, and one Makefile investigation from `embedded-engineer`.
- Confirm each subagent returns the required hand-off sections, can use the allow-listed read-only GitHub CLI and exact Git inspection commands, and cannot call other prohibited tools.
- For a persistent-data change, confirm the quality reviewer owns writer, marker, persistence-ordering, and test-coverage review. Request architecture analysis only for a distinct cross-module ownership, reader, migration, recovery, or state-flow question.
- Review the primary session to confirm the specialist outputs preserve context isolation and do not duplicate each other.

## Rollback

Remove the added global agent files and repository-inspection plugin, then remove the corresponding `plugin` and `subagent_depth` configuration entries before restarting OpenCode.

## Open Questions

- Which configured model should be the initial default for each pilot role after a small quality and context-isolation evaluation?
- Which concrete pilot tasks and evaluation criteria will determine whether to add the implementer, test designer, debugger, or hardware reviewer?
