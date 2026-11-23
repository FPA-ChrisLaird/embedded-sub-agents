# Embedded Subagents

Product-agnostic OpenCode V2 agent and subagent roles for embedded C/C++ software development. The roles are intended to be reusable across toolchains, RTOS and bare-metal systems, build systems, and hardware platforms.

## Repository Configuration

This repository is the version-controlled source of truth for the initial pilot. The executable configuration is in `.opencode/` and contains no secrets:

- `.opencode/opencode.json` sets `experimental.subagent_depth` to `1` and loads the local plugin.
- `.opencode/plugins/embedded-repository-inspection/index.ts` centrally defines the
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
- The [inspection plugin](.opencode/plugins/embedded-repository-inspection/index.ts)
  owns the shared shell policy. Its per-command rules are also generated into
  agent frontmatter so they do not depend on plugin activation order. The
  whole-command check requires the active plugin.
  Agent frontmatter owns each role's other tool permissions;
  [project configuration](.opencode/opencode.json) owns project defaults and
  nesting depth. A skill cannot override these rules.
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

OpenCode automatically loads the [project configuration](.opencode/opencode.json)
when started in this repository. It selects `embedded-engineer` as the default
agent but leaves the model to your OpenCode settings. Set `model` in your global
`opencode.json(c)` for new sessions, or use `/models` to switch an existing
session. The [specialist agents](.opencode/agents/) use the F&P AI Gateway
(`fpa-gateway`): GPT 6.2 Sol for architecture and C quality review, and GPT 6 Luna
for build analysis. The gateway must be available in the project to delegate to
them. Leave GPT 6 Luna on the gateway default: the gateway accepted requests
with both valid and invalid effort values, so support for an override is
unverified. To use the tested `xhigh` effort for GPT 6.2 Sol, merge the following
into your global `opencode.json(c)`. This applies to all agents using that model,
without requiring a `#variant` selector:

```json
{
  "providers": {
    "fpa-gateway": {
      "models": {
        "gpt-6.2-sol": {
          "body": { "reasoning": { "effort": "xhigh" } }
        }
      }
    }
  }
}
```

To install the agent suite globally, run the cross-platform Python 3 installer
from the repository root:

```powershell
py -3 .\scripts\install_opencode_agents.py
```

```sh
python3 ./scripts/install_opencode_agents.py
```

The installer copies the four agent files, shared plugin, and on-demand `android-device-workflow` and `erd-knowledge` skills to `~/.config/opencode/` (or `$XDG_CONFIG_HOME/opencode` when set). Skills are installed before agents. It does not rewrite user configuration, so it preserves credentials, providers, models, MCP servers, and unrelated settings. Rerun it after pulling an update to refresh the managed files. Use `--dry-run` to preview changes or `--config-dir PATH` for a non-standard or test location. A global `agents.<id>.disabled: true` override can intentionally keep an agent unavailable during an A/B comparison with built-in Plan and Build. OpenCode V2 reloads watched configuration automatically; use `/reload` to force a reload.

### Opt in to a local ERD checkout

Pass `--erd-checkout PATH` to authorize `embedded-engineer` to consult one
trusted ERD specification checkout without an external-directory prompt and
deny OpenCode edit, write, and patch operations against that external path.
For example, from PowerShell:

```powershell
py -3 .\scripts\install_opencode_agents.py --erd-checkout 'D:\path\to\documentation.erd-specification' --dry-run
```

Use your actual checkout directory, which must contain `README.md` and `erd/`.
Remove `--dry-run` to apply the change. The installer writes the resolved path
only into the local installed primary profile, not the repo or `opencode.json`.
On later installs, pass the same path again, or explicitly remove the local
rules with `--clear-erd-checkout`; the installer refuses to silently drop them.
The rules do not grant specialist access or replace shell approvals and are not
an operating-system read-only mount. They are intended for a firmware workspace
that uses the installed primary profile. A project that supplies its own
`embedded-engineer` profile (including this setup repo) can override the installed
rules. Use the ERD checkout as an external reference, not as an editing workspace.

### Migrating an existing V1 installation

These definitions use native V2 configuration and the V2 plugin API; do not
point OpenCode V1 at the converted files. Keep a copy of your V1 setup until
you have verified V2. See the [official migration guide](https://opencode.ai/docs/migrate-v1).

Run the installer with `--dry-run` first. It installs the native plugin directory
and renames the old managed `plugins/embedded-repository-inspection.ts` to a
non-loaded `.ts.v1-backup` file, preserving any local customization. Existing
backups are not overwritten; subsequent backups use numbered suffixes. The
installer never removes unrelated plugins or copies the repository's project
defaults over your global configuration.

OpenCode V2 disables task tracking by default. To enable `todowrite` for
`embedded-engineer` outside this checkout, set `"todo": true` in the top-level
`experimental` object of your global `opencode.json` or `opencode.jsonc`. Add
the object if it is missing, or merge the flag into the existing object without
replacing other settings. The installer does not set this flag. The three
analysis agents still deny `todowrite`.

If either global `opencode.json` or `opencode.jsonc` mentions the old `.ts`
plugin, the installer stops before writing anything. Manually replace that
entry with `./plugins/embedded-repository-inspection` under `plugins`, or remove
the entry to use automatic discovery, preserving all other settings. The check
is conservative and includes commented references. Then rerun the installer.

The installer also rejects a legacy plugin path that is a symlink, including
a dangling one, before copying any files.
Each file replacement is atomic, but the suite update is not a transaction;
if interrupted, resolve the reported error and rerun before relying on the suite.

Step limits, roles, and the shell safety policy are preserved. Permissions now
use ordered `permissions` rules with `shell` and `subagent` actions; MCP
permissions match the exact tool name registered by
OpenCode. V2 does not provide the former LSP diagnostics; use project
lint/compiler checks.
Skills remain in their existing V2-compatible layout and load on demand.

For a server named `codebase-memory-mcp`, OpenCode v2.2.7 keeps the hyphens
in permission actions such as `codebase-memory-mcp_search_graph`. Leave the
server's `codemode` setting at its default: OpenCode lists the individually
allowed tools directly for the specialists when their rules deny `execute`.
Only the primary has an explicit indexing allowance. Rerun the installer if
you use globally installed profiles outside this checkout.

OpenCode V2 can apply file-based agents after user plugin transforms. Therefore
the native frontmatter includes a generated copy of the shared per-command
rules, including their default and final denials. Missing or early-loading
plugins cannot silently remove those rules. After changing those rules in the
plugin, run `python scripts/sync_agent_shell_policy.py --write` and inspect the
generated agent diffs. The test suite checks exact policy equality and evaluates
its ordered outcomes; do not hand-edit the marked generated blocks.

Confirm all four agents are available in the target project. In an OpenCode
session opened there, run `/plugins` and check that
`embedded-repository-inspection` is active. Check its source path to see which
copy OpenCode loaded.

If you install globally and also work in this checkout, OpenCode V2 may report
`Duplicate plugin ID: embedded-repository-inspection`. If the global copy is
active, you can optionally skip the checkout copy with a
[path-specific `plugin.use` policy](https://opencode.ai/docs/policies#mcp-servers-skills-and-plugins).
Add this entry to `policies` in your global `opencode.json(c)`, preserving any
existing entries:

```json
{
  "action": "plugin.use",
  "resource": "/absolute/path/to/embedded-sub-agents/.opencode/plugins/embedded-repository-inspection",
  "effect": "deny"
}
```

Replace the example with the absolute path to the checkout's plugin directory
(escape Windows backslashes as `\\` in JSON). Match the directory, not the
plugin ID, so the global copy stays enabled. Run `/plugins` in the checkout
again and confirm only the global copy is listed and active. If you uninstall
the global copy, remove the rule so the checkout can load its own copy again.

With that rule in place, editing the plugin source in the checkout does not
change the running global copy. Use the isolated smoke tests below to try
plugin changes, then rerun the installer when you want those changes to take
effect globally. Reinstalling by itself does not resolve a duplicate ID.

Check delegation and approval behavior in a fresh session. Automated tests
cover configuration and plugin behavior with SDK-shaped fixtures by default.
To also test shell execution and specialist MCP tool discovery, set
`OPENCODE_SMOKE_TEST=1` in your environment and run
`python -m pytest tests/test_opencode_runtime_integration.py` with OpenCode V2
on `PATH`. These opt-in tests use an isolated standalone runtime and local
fixtures; they need no provider account or real MCP server.
The repository migration was checked with OpenCode v2.2.7: all four native agent
definitions and the local V2 plugin loaded, and the API returned the generated
shell rules. Global-only installation and conversational behavior still need
fresh-session verification after installation.

### Git inspection without prompts

The shared policy's native rules auto-approve individual, non-mutating Git inspection
commands, including status, safe diffs, shows and logs, reflog, branch and tag
listing, revision and reference queries, read-only configuration queries,
tracked-file and tree listing, blame, worktree listing, stash listing, and
submodule status. Use the plugin's canonical flags, such as
`git --no-optional-locks --no-pager status --short --branch` and
`git --no-pager diff --no-ext-diff --no-textconv <revision-or-path>`, so status
does not take an optional index lock and diffs cannot invoke external helpers or
repository-configured text-conversion filters.

Run inspection commands individually. OpenCode V2 checks permissions on each
extracted command, so the active plugin also checks the complete shell input
before execution for the four embedded agents. It conservatively rejects `&`,
`|`, `;`, and line breaks even inside quoted arguments. Without the plugin,
per-command permissions still apply, but they do not enforce this whole-call
restriction. Commands that can alter Git state—including staging,
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

The supported development and CI interpreter is Python 3.15; Python 3.13 is no longer a supported test target. Node.js 24 is also required for the offline TypeScript plugin contract tests (called by pytest). The repository uses Invoke to provide repeatable Python checks. Create and activate a virtual environment, install Invoke, then let `inv setup` install the pinned development tools and the pre-commit hook:

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install invoke
inv setup
```

```sh
python3.15 -m venv .venv
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

`inv setup` prepares developer tooling only; it does not install or overwrite the global OpenCode suite. Use `inv install-agents` for the default installation, or run `scripts/install_opencode_agents.py` directly when using `--dry-run`, `--config-dir`, or the ERD checkout options.

The [commit hook configuration](.pre-commit-config.yaml) runs Black, Flake8,
the full pytest suite (including for non-Python changes), and repository safety
checks. Black may reformat staged Python files and stop the commit so you can
inspect and restage them. The pytest hook uses an isolated environment with a
pinned dependency; activating the development virtual environment is not required
for that hook. `inv test` runs only pytest; `inv check` checks formatting and lint
as well, without reformatting files.

The [CI workflow](.github/workflows/python-checks.yml) runs `inv check` on
Python 3.15 using the pinned development requirements. The single job preserves
the required `Format, lint, and test` check name. When changing CI job names,
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
applicable by its native permissions generated from the
[inspection plugin](.opencode/plugins/embedded-repository-inspection/index.ts).
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
- [Primary agent](.opencode/agents/embedded-engineer.md): subagent allow-list,
  focused delegation, fan-out, persistence-review routing, and incomplete hand-offs.
- [Analysis agent definitions](.opencode/agents/): step limits, read-only tool
  permissions, and output contracts.
- [Inspection plugin](.opencode/plugins/embedded-repository-inspection/index.ts):
  shared shell rules.

Direct user invocation is not constrained by the primary's subagent routing, so
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
| `opencode`                   | `embedded-engineer`                                                                                            | Supplies current OpenCode V2 documentation for agent, skill, plugin, model, and permission configuration.                               | Load only for OpenCode work. Watched configuration reloads automatically; use `/reload` if needed.                                                                   |

## Recommended Delegation Boundaries

Use the skills to supply context and process, while each specialist retains ownership of the technical judgment.

| Agent / subagent                | Load by default | Load when prompted by the work                                                                                              | Do not delegate                                                                                                |
|---------------------------------|-----------------|-----------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| `embedded-engineer`             | None            | `opencode`, `create-spec`, `create-implementation-plan`, `use-jira`, `use-confluence`, `access-github`, Git workflow skills | Hardware conclusions without evidence from source, specifications, or a hardware reviewer                      |
| `embedded-architecture-analyst` | None            | `use-jira`, `use-confluence`, `create-spec`, `create-implementation-plan`, `access-github`                                  | Editing architecture or creating plans/specifications                                                          |
| `embedded-c-quality-reviewer`   | None            | `pr-check`, `access-github`, `use-xray`                                                                                     | Posting reviews, modifying suppressions, or resolving findings without evidence                                |
| `embedded-test-designer`        | None            | `use-xray`, `create-spec`, `markdown-table-formatting`                                                                      | Editing tests, running tests, or marking Xray results as passed                                                |
| `embedded-c-implementer`        | None            | `create-branch`, `commit-message-style`, `auto-commit-workflow` only when explicitly requested                              | Flashing, programming, device I/O, destructive targets, rebasing shared history                                |
| `embedded-build-analyzer`       | None            | `create-implementation-plan`, `access-github`, `markdown-table-formatting`                                                  | Running Make, clean, package, flash, or programming targets; reviewing or approving a whole pull request       |
| `embedded-debugger`             | None            | `use-jira`, `use-confluence`, `access-github`                                                                               | Running diagnostics against a device, changing configuration, or treating hypotheses as confirmed root causes  |
| `embedded-hardware-reviewer`    | None            | `use-jira`, `use-confluence`, `pr-check`                                                                                    | Accessing or programming hardware, or approving a change without datasheet and schematic evidence where needed |

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
