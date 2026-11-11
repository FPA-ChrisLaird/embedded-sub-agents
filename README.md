# Embedded Subagents

Product-agnostic OpenCode agent and subagent roles for embedded C/C++ software development. The roles are intended to be reusable across toolchains, RTOS and bare-metal systems, build systems, and hardware platforms.

## Repository Configuration

This repository is the version-controlled source of truth for the initial pilot. The executable configuration is in `.opencode/` and contains no secrets:

- `.opencode/opencode.json` sets `subagent_depth` to `1` and loads the local plugin.
- `.opencode/plugins/embedded-repository-inspection.ts` centrally applies the
  read-only GitHub CLI and bounded, non-mutating Git inspection policy. GitHub
  API writes require a separate permission prompt for the primary agent and
  are denied to analysis subagents; the primary also requires an explicit
  human request before making one.
- `.opencode/agents/embedded-engineer.md` defines the primary coordinator and
  permits it to create or refresh the trusted local Codebase Memory index
  without a prompt. The analysis subagents remain restricted to read-only
  Codebase Memory tools.
- `.opencode/agents/embedded-architecture-analyst.md` defines the read-only architecture analyst.
- `.opencode/agents/embedded-c-quality-reviewer.md` defines the read-only quality reviewer.
- `.opencode/agents/embedded-build-analyzer.md` defines the read-only Make and build-system analyst.
- `docs/workplans/Embedded-Subagent-Pilot-Charter.md` defines the pilot's purpose, boundaries, and acceptance criteria.
- `PLAN.md` tracks the pilot's remaining verification and evaluation tasks.

### Policy ownership

- [Agent definitions](.opencode/agents/) own role responsibilities, delegation,
  evidence standards, and permanent safety boundaries. The primary retains
  decisions and verification; the three analysis agents remain read-only.
- The [inspection plugin](.opencode/plugins/embedded-repository-inspection.ts)
  owns the shared enforced shell permission rules. Agent frontmatter owns each
  role's other tool permissions; [project configuration](.opencode/opencode.json)
  owns project defaults and nesting depth. A skill cannot override these rules.
- Each [on-demand skill](.opencode/skills/) owns its detailed workflow and
  safeguards. Load only relevant skills; do not copy their procedures into the
  permanent agent prompts or general documentation.
- This README is the installation and navigation guide. The
  [charter](docs/workplans/Embedded-Subagent-Pilot-Charter.md) records purpose and
  acceptance criteria; [PLAN.md](PLAN.md) tracks rollout and evaluation.
  Their summaries do not grant permissions or replace the operational sources.

When changing behavior, update its owning source and regression tests first,
then adjust links or scope summaries where needed. Keep the four-agent pilot
until recurring work demonstrates a need for a separate context boundary;
adding a skill does not add a device-execution agent.

OpenCode automatically loads this configuration when started in this repository. See [project configuration](.opencode/opencode.json) for the default agent/model and [agent frontmatter](.opencode/agents/) for role-specific models, reasoning variants, and step limits. These defaults are repository-scoped and do not rewrite global model preferences. To install the agent suite globally, run the cross-platform Python 3 installer from the repository root:

```powershell
py -3 .\scripts\install_opencode_agents.py
```

```sh
python3 ./scripts/install_opencode_agents.py
```

The installer copies the four agent files, shared plugin, and on-demand `android-device-workflow` and `erd-knowledge` skills to `~/.config/opencode/` (or `$XDG_CONFIG_HOME/opencode` when set). Skills are installed before agents. It does not remove files or rewrite `opencode.json`, so it preserves credentials, providers, models, MCP servers, and unrelated configuration. Rerun it after pulling an update to refresh the managed files. Use `--dry-run` to preview the changes or `--config-dir PATH` to install to a non-standard or test location. A global `disable: true` override can intentionally keep the suite unavailable during an A/B comparison with built-in Plan and Build. Quit and restart OpenCode after any configuration change.

### Git inspection without prompts

The shared plugin auto-approves individual, non-mutating Git inspection
commands, including status, safe diffs, shows and logs, reflog, branch and tag
listing, revision and reference queries, read-only configuration queries,
tracked-file and tree listing, blame, worktree listing, stash listing, and
submodule status. Use the plugin's canonical flags, such as
`git --no-optional-locks --no-pager status --short --branch` and
`git --no-pager diff --no-ext-diff --no-textconv <revision-or-path>`, so status
does not take an optional index lock and diffs cannot invoke external helpers or
repository-configured text-conversion filters.

Inspection commands must be invoked individually: shell composition (`&&`,
`||`, `;`, or `|`) remains denied so an approved read command cannot be combined
with an unreviewed action. Commands that can alter Git state—including staging,
committing, switching or creating branches, merging, rebasing, resetting,
cleaning, fetching, pulling, pushing, remote changes, and configuration
writes—are not auto-approved.

### Trusted external skills

The primary `embedded-engineer` auto-approves access to the trusted local skill
directory, `C:\Users\lairdc\.agents\**`, so loading installed skills does not
trigger an external-directory prompt. Other external paths still prompt, and
the analysis subagents remain denied external-directory access.

### On-demand ERD knowledge

The primary can load `erd-knowledge` for ERD lookup and payload interpretation.
The [ERD knowledge skill](.opencode/skills/erd-knowledge/SKILL.md) owns checkout
selection, source/version checks, shared-type resolution, interpretation rules,
and the output contract. It reads a user-selected live specification checkout
rather than embedding the catalogue, and complements `decode-gea-comms` for
transport captures. It does not authorize ERD writes or device operations.
Non-ERD tasks do not load its body; installation does not expand permissions.
For fresh-session behavioral checks and current validation limits, use the
[interactive ERD smoke test](docs/erd-skill-smoke-test.md).

## Development

The repository uses Invoke to provide repeatable Python checks. Create and activate a virtual environment, install Invoke, then let `inv setup` install the pinned development tools and the pre-commit hook:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install invoke
inv setup
```

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install invoke
inv setup
```

Use these commands from the repository root:

```text
inv format          Apply Black to tasks.py, scripts/, and tests/.
inv lint            Run Flake8 on the maintained Python sources.
inv test            Run the pytest suite.
inv check           Run Black --check, Flake8, and pytest without modifying files.
inv precommit       Run every pre-commit hook; formatting hooks may modify files.
inv install-agents  Run the default global OpenCode agent installer.
```

`inv setup` prepares developer tooling only; it does not install or overwrite the global OpenCode suite. Use `inv install-agents` for the default installation, or run `scripts/install_opencode_agents.py` directly when using `--dry-run` or `--config-dir`.

The [commit hook configuration](.pre-commit-config.yaml) runs Black, Flake8,
the full pytest suite (including for non-Python changes), and repository safety
checks. Black may reformat staged Python files and stop the commit so you can
inspect and restage them. The pytest hook uses an isolated environment with a
pinned dependency; activating the development virtual environment is not required
for that hook. `inv test` runs only pytest; `inv check` checks formatting and lint
as well, without reformatting files.

The [CI workflow](.github/workflows/python-checks.yml) runs `inv check` on each
Python version in its matrix using the pinned development requirements.
The aggregate `Format, lint, and test` gate preserves the required check name
and passes only when every matrix job succeeds. When changing CI job names,
verify that required status checks in branch protection still match.

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

The implemented role definitions are the authoritative catalogue:

- [Primary engineer](.opencode/agents/embedded-engineer.md): coordination and integration.
- [Architecture analyst](.opencode/agents/embedded-architecture-analyst.md): structure and execution contexts.
- [Quality reviewer](.opencode/agents/embedded-c-quality-reviewer.md): correctness and evidence.
- [Build analyzer](.opencode/agents/embedded-build-analyzer.md): build-system investigation.

Potential implementer, test-designer, debugger, and hardware-reviewer roles are
evaluation candidates in [PLAN.md](PLAN.md), not installed agents. Choose any
future model assignments through evaluation rather than an alternative-model
table that can drift from executable configuration.

Source formatting should remain deterministic tooling, such as `clang-format` or `uncrustify`, rather than an LLM agent.

Safety and approval boundaries are defined in the
[primary agent](.opencode/agents/embedded-engineer.md) and enforced where
applicable by the [inspection plugin](.opencode/plugins/embedded-repository-inspection.ts).
Firmware flashing remains prohibited; the primary owns approved build cleanup
and the scoped Android exception. Analysis agents remain read-only and cannot
access devices. See the owning files for exact rules, not this summary.

### Approved ADB application and log workflows

The [Android device workflow](.opencode/skills/android-device-workflow/SKILL.md)
owns the detailed authorization, build, device, transfer-path, launch-effect,
and context-budget safeguards. Its scope includes approved non-release APK
builds, APK transfers/installation, log capture, and installed-app launches;
UI automation remains outside that scope. The primary prompt requires loading
the skill before Android work and stopping if it is unavailable. Non-Android
tasks do not load its body. Skills do not waive shell approval or plugin denials.

## Delegation Controls

The primary agent may delegate focused, independent investigations. It should not create an unbounded hierarchy of agents or use subagents as a substitute for a decision owner.

For exact delegation rules, use these sources instead of a copied configuration:

- [Project configuration](.opencode/opencode.json): nesting depth.
- [Primary agent](.opencode/agents/embedded-engineer.md): task allow-list,
  focused delegation, fan-out, persistence-review routing, and incomplete hand-offs.
- [Analysis agent definitions](.opencode/agents/): step limits, read-only tool
  permissions, and output contracts.
- [Inspection plugin](.opencode/plugins/embedded-repository-inspection.ts):
  shared shell rules.

Direct user invocation is not constrained by the primary's task routing, so
each agent's own permissions remain necessary. The primary owns reconciliation
and final verification, not the specialist or the skill.

## Installed Skill Synergy

The currently available skills are primarily workflow, requirements, test-management, and GitHub integrations. They provide authoritative external context and repeatable process rules, but they do not replace embedded domain expertise. An agent should load a skill only when its trigger applies and its required integration is available. For all code and pull-request reviews, use `pr-check` exclusively; do not use `pr-review-github` or `review-pr-github`.

| Skill                        | Best-fit agent / subagent                                                                                      | Contribution                                                                                                                            | Permission and availability notes                                                                                                                                    |
|------------------------------|----------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `create-spec`                | `embedded-engineer`; `embedded-architecture-analyst`                                                           | Converts an approved requirement or Jira issue into a delivery contract with scope, constraints, acceptance criteria, and verification. | The primary engineer owns writing the specification. The architecture analyst may supply technical constraints and risks.                                            |
| `create-implementation-plan` | `embedded-engineer`; `embedded-architecture-analyst`; `embedded-build-analyzer`                                | Produces dependency-aware implementation tasks from an approved specification.                                                          | The primary engineer owns the plan. Architecture and build agents provide reviewed inputs, not product decisions.                                                    |
| `use-jira`                   | `embedded-engineer`; `embedded-architecture-analyst`; `embedded-debugger`; `embedded-hardware-reviewer`        | Retrieves requirements, acceptance criteria, defect history, and operational context for a change or failure.                           | Requires a Jira-capable MCP. Installed Atlassian MCPs are currently disabled. Read-only retrieval is suitable for analysts.                                          |
| `use-confluence`             | `embedded-engineer`; `embedded-architecture-analyst`; `embedded-debugger`; `embedded-hardware-reviewer`        | Retrieves interface specifications, architecture decisions, board information, timing requirements, and diagnostic procedures.          | Requires a Confluence-capable MCP. Installed Atlassian MCPs are currently disabled. Do not treat retrieved documents as code authority without reconciling versions. |
| `use-xray`                   | `embedded-test-designer`; `embedded-engineer`; `embedded-c-quality-reviewer`                                   | Maps test cases, plans, executions, and coverage to proposed regression and verification work.                                          | Requires an Xray MCP and credentials; its interface is read-only. Best paired with local test discovery and source analysis.                                         |
| `pr-check`                   | `embedded-c-quality-reviewer`; `embedded-hardware-reviewer`                                                    | Supplies a disciplined GitHub PR review workflow: diff scope, existing feedback, evidence validation, and C/C++ rule checks.            | Requires GitHub access. The quality reviewer owns the result; hardware agents may investigate delegated concerns.                                                    |
| `access-github`              | `embedded-engineer`; `embedded-architecture-analyst`; `embedded-c-quality-reviewer`; `embedded-build-analyzer` | Retrieves repository context, issues, pull-request status and diffs, and workflow status and logs through `gh`.                         | Requires GitHub authentication. Agents may use allow-listed read commands only; mutations remain denied or require explicit approval.                                |
| `my-open-prs`                | `embedded-engineer`; `embedded-c-quality-reviewer`                                                             | Finds open PRs the user has reviewed or commented on, enabling firmware-review follow-up.                                               | Requires GitHub authentication. It is a portfolio-level coordination aid, not a firmware-analysis capability.                                                        |
| `create-branch`              | `embedded-engineer`; `embedded-c-implementer`                                                                  | Applies the configured branch naming and base-branch convention before a bounded implementation change.                                 | Mutates Git state. Invoke only with an explicit request to create a branch and after confirming the repository workflow applies.                                     |
| `auto-commit-workflow`       | `embedded-engineer`; `embedded-c-implementer`                                                                  | Defines when to create focused commits after completed units of work.                                                                   | Conflicts with a no-auto-commit policy. Do not load unless the user explicitly requests commits or enables automatic commits.                                        |
| `commit-message-style`       | `embedded-engineer`; `embedded-c-implementer`                                                                  | Validates commit subject and body conventions before committing.                                                                        | Use only when a commit is explicitly requested or permitted. Does not authorize committing by itself.                                                                |
| `git-rebase-i`               | `embedded-engineer`                                                                                            | Provides a safe non-interactive procedure for restructuring local commits.                                                              | High-impact history rewrite. Do not delegate to an implementation subagent or use on shared/pushed commits without explicit approval.                                |
| `markdown-table-formatting`  | `embedded-engineer`; `embedded-test-designer`; `embedded-build-analyzer`                                       | Produces aligned Markdown tables in specifications, plans, test matrices, build-target summaries, and reports.                          | Deterministic local formatting only. It does not format C/C++ source.                                                                                                |
| `customize-opencode`         | `embedded-engineer`                                                                                            | Validates OpenCode agent, skill, command, plugin, model, and permission configuration before it is written.                             | Reserved for configuring this agent suite. Configuration changes require restarting OpenCode before they take effect.                                                |

## Recommended Delegation Boundaries

Use the skills to supply context and process, while each specialist retains ownership of the technical judgment.

| Agent / subagent                | Load by default      | Load when prompted by the work                                                                                  | Do not delegate                                                                                                |
|---------------------------------|----------------------|-----------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| `embedded-engineer`             | `customize-opencode` | `create-spec`, `create-implementation-plan`, `use-jira`, `use-confluence`, `access-github`, Git workflow skills | Hardware conclusions without evidence from source, specifications, or a hardware reviewer                      |
| `embedded-architecture-analyst` | None                 | `use-jira`, `use-confluence`, `create-spec`, `create-implementation-plan`, `access-github`                      | Editing architecture or creating plans/specifications                                                          |
| `embedded-c-quality-reviewer`   | None                 | `pr-check`, `access-github`, `use-xray`                                                                         | Posting reviews, modifying suppressions, or resolving findings without evidence                                |
| `embedded-test-designer`        | None                 | `use-xray`, `create-spec`, `markdown-table-formatting`                                                          | Editing tests, running tests, or marking Xray results as passed                                                |
| `embedded-c-implementer`        | None                 | `create-branch`, `commit-message-style`, `auto-commit-workflow` only when explicitly requested                  | Flashing, programming, device I/O, destructive targets, rebasing shared history                                |
| `embedded-build-analyzer`       | None                 | `create-implementation-plan`, `access-github`, `markdown-table-formatting`                                      | Running Make, clean, package, flash, or programming targets; reviewing or approving a whole pull request       |
| `embedded-debugger`             | None                 | `use-jira`, `use-confluence`, `access-github`                                                                   | Running diagnostics against a device, changing configuration, or treating hypotheses as confirmed root causes  |
| `embedded-hardware-reviewer`    | None                 | `use-jira`, `use-confluence`, `pr-check`                                                                        | Accessing or programming hardware, or approving a change without datasheet and schematic evidence where needed |

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
