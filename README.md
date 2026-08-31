# Embedded Subagents

Product-agnostic OpenCode agent and subagent roles for embedded C/C++ software development. The roles are intended to be reusable across toolchains, RTOS and bare-metal systems, build systems, and hardware platforms.

## Repository Configuration

This repository is the version-controlled source of truth for the initial pilot. The executable configuration is in `.opencode/` and contains no secrets:

- `.opencode/opencode.json` sets `subagent_depth` to `1`.
- `.opencode/agents/embedded-engineer.md` defines the primary coordinator.
- `.opencode/agents/embedded-architecture-analyst.md` defines the read-only architecture analyst.
- `.opencode/agents/embedded-c-quality-reviewer.md` defines the read-only quality reviewer.
- `.opencode/agents/embedded-build-analyzer.md` defines the read-only Make and build-system analyst.

OpenCode automatically loads this configuration when started in this repository. It deliberately does not set `default_agent`, so existing user preferences remain unchanged; select `embedded-engineer` explicitly when using the pilot. To install the same suite globally, copy the agent files to `~/.config/opencode/agents/` and merge the `subagent_depth` setting into `~/.config/opencode/opencode.json`; do not copy credentials or provider settings from another configuration. Quit and restart OpenCode after any configuration change.

The current pilot implements only these four roles. The other roles in the catalogue are future candidates and are not yet available for automatic delegation.

## Why Subagents

Context isolation is a primary reason to use subagents. Each subagent begins with a focused task and fresh context, investigates the workspace independently, and returns only its relevant evidence and conclusions. This keeps large source trees, generated build output, datasheets, compiler logs, and alternative hypotheses out of the primary engineer's working context.

| Situation                                           | Context-isolation benefit                                                                                                     |
|-----------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| Legacy firmware architecture discovery              | The architecture analyst can traverse a broad codebase without displacing the primary task's requirements and decisions.      |
| Deep Makefile, script, or toolchain investigation   | Include graphs, variable expansion, generated artefacts, and command output remain contained in the build analysis.           |
| Independent safety or correctness review            | The quality reviewer can challenge implementation assumptions without inheriting the primary agent's implementation momentum. |
| Failure triage using logs, traces, and CI artefacts | The debugger can examine noisy evidence and return ranked hypotheses, preserving the primary context for resolution work.     |
| Multiple independent lines of investigation         | Specialists can work in parallel and return concise results for the primary engineer to reconcile.                            |

Subagents do not have authority over the final design or change. The `embedded-engineer` retains the requirements, decisions, cross-cutting trade-offs, integration work, and final verification.

| Agent / subagent                | Mode     | Responsibilities / coverage                                                                                                              | Generation / permissions                                  | Default model | Selective alternatives                                                                   |
|---------------------------------|----------|------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|---------------|------------------------------------------------------------------------------------------|
| `embedded-engineer`             | Primary  | Coordinates investigations, selects safe changes, delegates work, integrates results, and verifies implementations.                      | Edits allowed; commands ask; flash and device I/O denied. | GPT-5.6 Terra | Claude Sonnet 5; Gemini 3.1 Pro                                                          |
| `embedded-architecture-analyst` | Subagent | Maps execution contexts and dependencies; assesses state machines, ISR hand-off, HAL boundaries, configuration, and resources.           | Returns analysis and design options; read-only.           | GPT-5.6 Terra | Gemini 3.1 Pro; Claude Sonnet 5                                                          |
| `embedded-c-quality-reviewer`   | Subagent | Reviews correctness, concurrency, integer safety, undefined behavior, timing, memory, register effects, lint/MISRA, and static analysis. | Returns evidence-backed findings; read-only.              | GPT-5.6 Terra | Grok 4.6 for independent counter-review; Claude Sonnet 5; Claude Opus 4.8/5; GPT-5.6 Sol |
| `embedded-test-designer`        | Subagent | Designs host and target tests, mocks, fakes, boundary conditions, fault injection, coverage improvements, and regression tests.          | Drafts test code and plans in its response; read-only.    | GPT-5.6 Terra | GPT-5.3 Codex; Claude Sonnet 5; Gemini 3.1 Pro                                           |
| `embedded-c-implementer`        | Subagent | Implements a tightly bounded firmware or test change, preserving local conventions and reporting verification.                           | Edits allowed; commands ask; flash and device I/O denied. | GPT-5.6 Terra | GPT-5.3 Codex; Claude Sonnet 5                                                           |
| `embedded-build-analyzer`       | Subagent | Traces Makefiles, scripts, toolchains, flags, targets, variants, artifacts, dependencies, and unsafe commands.                           | Reports safe commands and risks; read-only.               | GPT-5.6 Luna  | DeepSeek V4 Pro; Gemini 3.1 Flash-Lite; Gemini 3 Flash; Gemini 3.5 Flash; GPT-5.6 Terra  |
| `embedded-debugger`             | Subagent | Diagnoses compiler and test failures, logs, crashes, watchdog resets, protocol traces, and suspected hardware interactions.              | Returns ranked root-cause hypotheses; read-only.          | GPT-5.6 Terra | Grok 4.6 for independent diagnosis; Claude Sonnet 5; GPT-5.6 Luna for log triage         |
| `embedded-hardware-reviewer`    | Subagent | Reviews HAL and driver changes for register access, initialization order, interrupt configuration, pin safety, and assumptions.          | Returns risks and required datasheet checks; read-only.   | GPT-5.6 Terra | Gemini 3.1 Pro; Claude Sonnet 5                                                          |

Use Grok 4.6 only when an independent reasoning path is valuable: a high-consequence quality finding or a difficult diagnosis where the primary model has already produced a hypothesis. Use GPT-5.6 Sol only as a final escalation for a difficult, high-consequence, multi-module decision that remains uncertain after evidence-based Terra analysis. Do not select either model as the default for routine exploration, implementation, build analysis, test design, or hardware review.

Source formatting should remain deterministic tooling, such as `clang-format` or `uncrustify`, rather than an LLM agent.

All agents should explicitly deny firmware flashing, programming, device I/O, and destructive build targets. Read-only subagents may generate reports, design options, and code proposals in their responses, but cannot modify the workspace or execute commands.

## Delegation Controls

The primary agent may delegate focused, independent investigations. It should not create an unbounded hierarchy of agents or use subagents as a substitute for a decision owner.

| Control                   | Recommended configuration or prompt rule                                                                                                                                                               | Effect                                                                                                    |
|---------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| Nesting depth             | Set top-level `subagent_depth` to `1`.                                                                                                                                                                 | The primary agent may launch a subagent; a subagent cannot launch another subagent.                       |
| Subagent task permission  | Set `task: deny` in every subagent's permissions.                                                                                                                                                      | Provides a per-agent defence in depth against recursive delegation.                                       |
| Primary task allow-list   | Deny `task: "*"` first, then allow named analysis agents; set `embedded-c-implementer` to `ask`.                                                                                                       | Limits automatic delegation to the defined suite and requires approval before assigning implementation.   |
| Per-agent iteration limit | Use `steps`: primary `30`; quality reviewer and implementer `20`; all other subagents `12`.                                                                                                            | Bounds tool-use iterations. On reaching the limit, OpenCode requires the agent to return a summary.       |
| Parallel fan-out          | In the `embedded-engineer` prompt: launch at most three independent subagents for one user request. Do not delegate overlapping work.                                                                  | Contains cost and prevents duplicated investigations. OpenCode does not currently expose a fan-out limit. |
| Delegation input          | Give each subagent one question, relevant paths or artefacts, constraints, and its expected output. Do not delegate an undifferentiated repository-wide task.                                          | Preserves context isolation and makes the result actionable.                                              |
| Delegation output         | Require scope, evidence, assumptions, risks, and a recommended next action; use a concise word limit appropriate to the task.                                                                          | Keeps child-session findings from overwhelming the primary context.                                       |
| Direct user invocation    | Keep safety permissions on every subagent. `task` rules control model delegation only; users can still invoke an agent directly with `@`, even when the primary's `task` permission denies that agent. | Treat task permissions as routing controls, not a security boundary.                                      |

This configuration establishes the recommended delegation boundary:

```json
{
  "subagent_depth": 1,
  "agent": {
    "embedded-engineer": {
      "mode": "primary",
      "steps": 30,
      "permission": {
        "task": {
          "*": "deny",
          "embedded-architecture-analyst": "allow",
          "embedded-c-quality-reviewer": "allow",
          "embedded-build-analyzer": "allow",
          "embedded-c-implementer": "ask"
        }
      }
    }
  }
}
```

Each subagent should set `mode: subagent`, its role-appropriate `steps` value, and `permission.task: deny`. The primary agent should reconcile conflicting findings and remain responsible for final technical decisions, changes, and verification.

## Installed Skill Synergy

The currently available skills are primarily workflow, requirements, test-management, and GitHub integrations. They provide authoritative external context and repeatable process rules, but they do not replace embedded domain expertise. An agent should load a skill only when its trigger applies and its required integration is available.

| Skill                        | Best-fit agent / subagent                                                                               | Contribution                                                                                                                            | Permission and availability notes                                                                                                                                    |
|------------------------------|---------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `create-spec`                | `embedded-engineer`; `embedded-architecture-analyst`                                                    | Converts an approved requirement or Jira issue into a delivery contract with scope, constraints, acceptance criteria, and verification. | The primary engineer owns writing the specification. The architecture analyst may supply technical constraints and risks.                                            |
| `create-implementation-plan` | `embedded-engineer`; `embedded-architecture-analyst`; `embedded-build-analyzer`                         | Produces dependency-aware implementation tasks from an approved specification.                                                          | The primary engineer owns the plan. Architecture and build agents provide reviewed inputs, not product decisions.                                                    |
| `use-jira`                   | `embedded-engineer`; `embedded-architecture-analyst`; `embedded-debugger`; `embedded-hardware-reviewer` | Retrieves requirements, acceptance criteria, defect history, and operational context for a change or failure.                           | Requires a Jira-capable MCP. Installed Atlassian MCPs are currently disabled. Read-only retrieval is suitable for analysts.                                          |
| `use-confluence`             | `embedded-engineer`; `embedded-architecture-analyst`; `embedded-debugger`; `embedded-hardware-reviewer` | Retrieves interface specifications, architecture decisions, board information, timing requirements, and diagnostic procedures.          | Requires a Confluence-capable MCP. Installed Atlassian MCPs are currently disabled. Do not treat retrieved documents as code authority without reconciling versions. |
| `use-xray`                   | `embedded-test-designer`; `embedded-engineer`; `embedded-c-quality-reviewer`                            | Maps test cases, plans, executions, and coverage to proposed regression and verification work.                                          | Requires an Xray MCP and credentials; its interface is read-only. Best paired with local test discovery and source analysis.                                         |
| `pr-check`                   | `embedded-c-quality-reviewer`; `embedded-hardware-reviewer`; `embedded-build-analyzer`                  | Supplies a disciplined GitHub PR review workflow: diff scope, existing feedback, evidence validation, and C/C++ rule checks.            | Requires GitHub access. The quality reviewer owns the result; hardware and build agents may investigate delegated concerns.                                          |
| `pr-review-github`           | `embedded-c-quality-reviewer`; `embedded-hardware-reviewer`                                             | Supports evidence-based GitHub review, including resolved-thread checks and optional review submission.                                 | Overlaps with `pr-check`; use one canonical PR-review skill to avoid duplicate process. Posting always requires explicit user approval.                              |
| `review-pr-github`           | `embedded-c-quality-reviewer`; `embedded-hardware-reviewer`                                             | Alternative GitHub PR-review workflow for deep review and existing-thread triage.                                                       | Functionally overlaps with `pr-check` and `pr-review-github`; do not load alongside either for the same review.                                                      |
| `access-github`              | `embedded-engineer`; `embedded-c-quality-reviewer`; `embedded-debugger`; `embedded-build-analyzer`      | Retrieves repositories, pull requests, issues, workflow status, releases, and CI logs through `gh`.                                     | Requires GitHub authentication. Read-only agents may retrieve evidence; only the primary engineer should create or modify remote artefacts.                          |
| `my-open-prs`                | `embedded-engineer`; `embedded-c-quality-reviewer`                                                      | Finds open PRs the user has reviewed or commented on, enabling firmware-review follow-up.                                               | Requires GitHub authentication. It is a portfolio-level coordination aid, not a firmware-analysis capability.                                                        |
| `create-branch`              | `embedded-engineer`; `embedded-c-implementer`                                                           | Applies the configured branch naming and base-branch convention before a bounded implementation change.                                 | Mutates Git state. Invoke only with an explicit request to create a branch and after confirming the repository workflow applies.                                     |
| `auto-commit-workflow`       | `embedded-engineer`; `embedded-c-implementer`                                                           | Defines when to create focused commits after completed units of work.                                                                   | Conflicts with a no-auto-commit policy. Do not load unless the user explicitly requests commits or enables automatic commits.                                        |
| `commit-message-style`       | `embedded-engineer`; `embedded-c-implementer`                                                           | Validates commit subject and body conventions before committing.                                                                        | Use only when a commit is explicitly requested or permitted. Does not authorize committing by itself.                                                                |
| `git-rebase-i`               | `embedded-engineer`                                                                                     | Provides a safe non-interactive procedure for restructuring local commits.                                                              | High-impact history rewrite. Do not delegate to an implementation subagent or use on shared/pushed commits without explicit approval.                                |
| `markdown-table-formatting`  | `embedded-engineer`; `embedded-test-designer`; `embedded-build-analyzer`                                | Produces aligned Markdown tables in specifications, plans, test matrices, build-target summaries, and reports.                          | Deterministic local formatting only. It does not format C/C++ source.                                                                                                |
| `customize-opencode`         | `embedded-engineer`                                                                                     | Validates OpenCode agent, skill, command, plugin, model, and permission configuration before it is written.                             | Reserved for configuring this agent suite. Configuration changes require restarting OpenCode before they take effect.                                                |

## Recommended Delegation Boundaries

Use the skills to supply context and process, while each specialist retains ownership of the technical judgment.

| Agent / subagent                | Load by default      | Load when prompted by the work                                                                                  | Do not delegate                                                                                                |
|---------------------------------|----------------------|-----------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| `embedded-engineer`             | `customize-opencode` | `create-spec`, `create-implementation-plan`, `use-jira`, `use-confluence`, `access-github`, Git workflow skills | Hardware conclusions without evidence from source, specifications, or a hardware reviewer                      |
| `embedded-architecture-analyst` | None                 | `use-jira`, `use-confluence`, `create-spec`, `create-implementation-plan`                                       | Editing architecture or creating plans/specifications                                                          |
| `embedded-c-quality-reviewer`   | None                 | `pr-check` or one PR-review alternative, `access-github`, `use-xray`                                            | Posting reviews, modifying suppressions, or resolving findings without evidence                                |
| `embedded-test-designer`        | None                 | `use-xray`, `create-spec`, `markdown-table-formatting`                                                          | Editing tests, running tests, or marking Xray results as passed                                                |
| `embedded-c-implementer`        | None                 | `create-branch`, `commit-message-style`, `auto-commit-workflow` only when explicitly requested                  | Flashing, programming, device I/O, destructive targets, rebasing shared history                                |
| `embedded-build-analyzer`       | None                 | `create-implementation-plan`, `access-github`, `markdown-table-formatting`                                      | Running Make, clean, package, flash, or programming targets in the read-only pilot                             |
| `embedded-debugger`             | None                 | `use-jira`, `use-confluence`, `access-github`                                                                   | Running diagnostics against a device, changing configuration, or treating hypotheses as confirmed root causes  |
| `embedded-hardware-reviewer`    | None                 | `use-jira`, `use-confluence`, `pr-check` or one PR-review alternative                                           | Accessing or programming hardware, or approving a change without datasheet and schematic evidence where needed |

## Embedded Skills To Add

The following product-agnostic skills would address the gaps in the current set. They should encode repeatable investigation procedures and output contracts, rather than duplicate an agent's general reasoning role.

| Proposed skill                    | Primary consumers                                                                     | Purpose                                                                                                                                             |
|-----------------------------------|---------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| `embedded-c-code-review`          | `embedded-c-quality-reviewer`; `embedded-hardware-reviewer`                           | Repeatable checklist for interrupt safety, atomicity, integer conversion, undefined behavior, initialization, time wraparound, and register access. |
| `embedded-make-build-analysis`    | `embedded-build-analyzer`; `embedded-debugger`; `embedded-c-implementer`              | Procedure to trace include graphs, variable expansion, toolchain selection, configuration branches, target effects, and hazardous targets.          |
| `embedded-test-strategy`          | `embedded-test-designer`; `embedded-c-implementer`; `embedded-c-quality-reviewer`     | Separates host and target verification; specifies mocking, fault injection, time control, and coverage evidence.                                    |
| `embedded-static-analysis`        | `embedded-c-quality-reviewer`; `embedded-c-implementer`                               | Identifies available linters, rule sets, suppressions, baselines, MISRA deviations, and a defensible finding-triage process.                        |
| `embedded-toolchain-discovery`    | `embedded-build-analyzer`; `embedded-debugger`; `embedded-c-implementer`              | Identifies compilers, linkers, programming tools, SDKs, environment requirements, and safe non-mutating discovery commands.                         |
| `embedded-hardware-change-review` | `embedded-hardware-reviewer`; `embedded-c-quality-reviewer`; `embedded-c-implementer` | Reviews peripheral ownership, reset state, pin safety, ISR priority, clock dependencies, and required artefact evidence.                            |

Do not create these skills until a recurring workflow exposes the exact organisation-specific conventions, tools, and expected outputs they need to enforce.
