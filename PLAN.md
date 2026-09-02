# Embedded Subagent Pilot Plan

This plan implements the product-agnostic embedded subagent pilot chartered in [Embedded-Subagent-Pilot-Charter.md](docs/workplans/Embedded-Subagent-Pilot-Charter.md) and described in [README.md](README.md). It is a configuration rollout, not a firmware change.

## Decisions

- Use global OpenCode agent files so the roles are reusable across embedded product repositories.
- Set `subagent_depth` to `1`: the primary agent may delegate, but no subagent may delegate further.
- Start with four roles: `embedded-engineer`, `embedded-architecture-analyst`, `embedded-c-quality-reviewer`, and `embedded-build-analyzer`.
- Make analysis roles read-only. Add `embedded-c-implementer` only after the analysis pilot produces reliable, useful hand-offs.
- Prohibit hardware programming, device I/O, and destructive build targets for every role. The primary requires approval for non-allow-listed commands; recognised flashing, programming, clean, package, and release patterns remain hard-denied.
- Do not enable Jira, Confluence, or Xray retrieval for subagents during the initial pilot. Allow only read-only GitHub CLI retrieval plus exact non-mutating Git inspection commands for repository context, issues, pull-request status and diffs, Actions status and logs, and local repository state.
- Use GPT-5.6 Terra with `xhigh` for `embedded-engineer`, `embedded-c-quality-reviewer`, and `embedded-architecture-analyst`; use GPT-5.6 Luna with `medium` for `embedded-build-analyzer`.
- Do not create embedded-specific skills until repeated work demonstrates the organisational conventions they must encode.

## Tasks

- [x] Create and version-control `embedded-engineer` in `.opencode/agents/`, then install it globally at `C:\Users\lairdc\.config\opencode\agents\`.
  - Configure it as an unlimited primary agent so it can reconcile and verify specialist findings.
  - Allow only the defined analysis agents through `permission.task`; require approval for any future implementer delegation.
  - Limit each user request to three independent subagents and require focused inputs and concise hand-offs.
  - Preserve final responsibility for requirements, decisions, integration, and verification.

- [x] Create and version-control the read-only analysis agents in `.opencode/agents/`, then install them globally at `C:\Users\lairdc\.config\opencode\agents\`.
  - `embedded-architecture-analyst.md`: map execution contexts, dependencies, boundaries, configuration, and resource trade-offs.
  - `embedded-c-quality-reviewer.md`: review correctness, concurrency, timing, integer safety, undefined behavior, and static-analysis evidence.
  - `embedded-build-analyzer.md`: trace Makefiles, scripts, toolchains, targets, artefacts, and hazardous commands.
  - Set `mode: subagent`, `permission.task: deny`, and `edit: deny` on each agent.
  - Allow workspace read, glob, grep, and list operations. The shared repository-inspection plugin appends read-only `gh` and exact non-mutating Git inspection command allow-lists; it denies all other shell commands.
  - Set `steps: 20` for the architecture analyst and quality reviewer, and `steps: 12` for the build analyzer.
  - Require every response to state scope, evidence, assumptions, risks, and recommended next action. Quality reviews must separately state residual risks.

- [x] Add and version-control the delegation configuration in `.opencode/opencode.json`, then merge it into `C:\Users\lairdc\.config\opencode\opencode.json`.
  - Set `subagent_depth` to `1`.
  - Load the local shared repository-inspection plugin, then install its matching global file.
  - Centralize baseline shell policy, recognised firmware/build safety denials, GitHub CLI access, and exact non-mutating Git inspection rules in the plugin: unlisted primary shell commands and mutation-shaped API calls require approval; subagent commands beyond the allow-list are denied.
  - Add an explicit task allow-list to the `embedded-engineer` agent definition with a catch-all deny rule first.
  - Keep all non-pilot agents unavailable to automatic delegation.
  - Preserve existing configuration and validate against the OpenCode schema before saving.

- [ ] Restart the interactive OpenCode session and verify agent discovery.
  - [x] A fresh, global-only `opencode agent list` process has confirmed agent discovery and the effective shared GitHub permission rules.
  - Confirm the primary agent and three analysis subagents are visible with the intended modes and permissions.
  - Confirm analysis subagents cannot edit, run local shell commands, or launch child agents; confirm they can run only the allow-listed read-only `gh` and Git inspection commands.
  - Confirm the primary agent can delegate only to the configured analysis roles.

- [ ] Run the pilot against representative embedded-C tasks.
  - Ask the architecture analyst to map an unfamiliar firmware module, including ISR/task/main-loop boundaries.
  - Ask the quality reviewer to review a bounded change involving timing, state, or concurrency.
  - Ask the build analyzer to trace an unfamiliar Makefile entry point and identify safe non-mutating commands.
  - Use one primary-agent session to reconcile the three reports and record whether their conclusions are actionable.
  - Review a change to versioned persistent data and verify that the quality reviewer enumerates all writers, proves version-marker coupling, and rejects unproven event-ordering dependencies. If an architecture report is needed, verify that it covers only distinct cross-module ownership, reader, migration, recovery, or state-flow questions.

- [ ] Evaluate the pilot before expanding the suite.
  - Measure whether the hand-offs preserve primary-session context, avoid duplicated investigation, and provide actionable evidence.
  - Assess whether the selected models, reasoning variants, step limits, and three-agent fan-out yield sufficient results without unnecessary cost or incomplete hand-offs.
  - Confirm that any requested permission change is supported by pilot evidence and preserves the read-only subagent and hazardous-command boundaries.
  - Record the evaluation and any resulting configuration changes before adding roles or embedded-specific skills.

- [ ] Add roles only when a recurring workflow justifies them.
  - Add `embedded-c-implementer` for tightly bounded edits and test changes after the read-only pilot succeeds.
  - Add `embedded-test-designer` for recurring host/target test planning.
  - Add `embedded-debugger` for recurring failure triage using logs and traces.
  - Add `embedded-hardware-reviewer` only where relevant datasheets, schematics, and interface specifications are available.
  - Apply the same depth, task-denial, safety, iteration, and hand-off rules to every new subagent.

- [ ] Add embedded-specific skills only after the roles expose a repeatable procedure.
  - Prioritise `embedded-make-build-analysis`, `embedded-c-code-review`, and `embedded-test-strategy`.
  - Keep each skill product-agnostic, tool-aware, and limited to a repeatable workflow with a clear output contract.
  - Add project-specific rules, toolchain commands, and hardware documents through project configuration or references rather than global skills.

## Verification

- The OpenCode configuration validates and loads after restart.
- `subagent_depth` is `1` and every subagent has `permission.task: deny`.
- The primary agent's task permission has a deny-by-default allow-list.
- Read-only pilot agents can inspect the workspace, use allow-listed read-only GitHub CLI and exact Git inspection commands, but cannot edit files, execute local shell commands, or create nested subagents.
- Pilot reports are concise, evidence-based, and useful to the primary engineer without requiring repeated repository exploration.
- Quality-review hand-offs identify residual risks separately from findings and evidence gaps.
- The primary resumes an exhausted subagent or resolves its remaining review gap before finalising.
- Versioned persistent-data reviews trace every writer and identify unproven event ordering that can persist incompatible data.
- Roles prohibit flashing firmware, programming devices, device I/O, and destructive build targets. Recognised flashing, programming, clean, package, and release command patterns are hard-denied; other primary shell commands require human approval.

## Out Of Scope

- Firmware, build-system, or hardware changes.
- Enabling third-party MCP integrations for subagents.
- Automated commits, pushes, pull-request comments, or history rewriting.
- Automatic source formatting or replacing deterministic formatters with an LLM.
