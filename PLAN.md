# Embedded Subagent Pilot Plan

This plan implements the product-agnostic embedded subagent pilot specified in [WIP-embedded-subagent-pilot-Spec.md](docs/workplans/WIP-embedded-subagent-pilot-Spec.md) and described in [README.md](README.md). It is a configuration rollout, not a firmware change.

## Decisions

- Use global OpenCode agent files so the roles are reusable across embedded product repositories.
- Set `subagent_depth` to `1`: the primary agent may delegate, but no subagent may delegate further.
- Start with four roles: `embedded-engineer`, `embedded-architecture-analyst`, `embedded-c-quality-reviewer`, and `embedded-build-analyzer`.
- Make analysis roles read-only. Add `embedded-c-implementer` only after the analysis pilot produces reliable, useful hand-offs.
- Keep hardware programming, device I/O, and destructive build targets denied for every role.
- Do not enable Jira, Confluence, Xray, or GitHub retrieval for subagents during the initial pilot.
- Do not create embedded-specific skills until repeated work demonstrates the organisational conventions they must encode.

## Tasks

- [x] Create and version-control `embedded-engineer` in `.opencode/agents/`, then install it globally at `C:\Users\lairdc\.config\opencode\agents\`.
  - Configure it as a primary agent with `steps: 30`.
  - Allow only the defined analysis agents through `permission.task`; require approval for any future implementer delegation.
  - Limit each user request to three independent subagents and require focused inputs and concise hand-offs.
  - Preserve final responsibility for requirements, decisions, integration, and verification.

- [x] Create and version-control the read-only analysis agents in `.opencode/agents/`, then install them globally at `C:\Users\lairdc\.config\opencode\agents\`.
  - `embedded-architecture-analyst.md`: map execution contexts, dependencies, boundaries, configuration, and resource trade-offs.
  - `embedded-c-quality-reviewer.md`: review correctness, concurrency, timing, integer safety, undefined behavior, and static-analysis evidence.
  - `embedded-build-analyzer.md`: trace Makefiles, scripts, toolchains, targets, artefacts, and hazardous commands.
  - Set `mode: subagent`, `permission.task: deny`, `edit: deny`, and `bash: deny` on each agent.
  - Allow only workspace read, glob, grep, and list operations.
  - Set `steps: 20` for the quality reviewer and `steps: 12` for the other analysis agents.
  - Require every response to state scope, evidence, assumptions, risks, and recommended next action.

- [x] Add and version-control the delegation configuration in `.opencode/opencode.json`, then merge it into `C:\Users\lairdc\.config\opencode\opencode.json`.
  - Set `subagent_depth` to `1`.
  - Add an explicit task allow-list to the `embedded-engineer` agent definition with a catch-all deny rule first.
  - Keep all non-pilot agents unavailable to automatic delegation.
  - Preserve existing configuration and validate against the OpenCode schema before saving.

- [ ] Restart the interactive OpenCode session and verify agent discovery.
  - A fresh `opencode agent list` process has confirmed agent discovery.
  - Confirm the primary agent and three analysis subagents are visible with the intended modes and permissions.
  - Confirm analysis subagents cannot edit, run shell commands, or launch child agents.
  - Confirm the primary agent can delegate only to the configured analysis roles.

- [ ] Run the pilot against representative embedded-C tasks.
  - Ask the architecture analyst to map an unfamiliar firmware module, including ISR/task/main-loop boundaries.
  - Ask the quality reviewer to review a bounded change involving timing, state, or concurrency.
  - Ask the build analyzer to trace an unfamiliar Makefile entry point and identify safe non-mutating commands.
  - Use one primary-agent session to reconcile the three reports and record whether their conclusions are actionable.

- [ ] Evaluate the pilot before expanding the suite.
  - Measure whether the hand-offs preserve primary-session context, avoid duplicated investigation, and identify useful evidence.
  - Compare model quality and cost for the assigned roles, including GPT-5.6 Terra, GPT-5.6 Luna, and Grok 4.6.
  - Refine prompts, `steps`, and the three-agent fan-out limit based on observed behaviour.
  - Do not grant command execution because a prompt requests it; use explicit permission changes justified by pilot evidence.

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
- Read-only pilot agents can inspect the workspace but cannot edit files, execute shell commands, or create nested subagents.
- Pilot reports are concise, evidence-based, and useful to the primary engineer without requiring repeated repository exploration.
- No role can flash firmware, program devices, access device I/O, or run destructive build targets.

## Out Of Scope

- Firmware, build-system, or hardware changes.
- Enabling third-party MCP integrations for subagents.
- Automated commits, pushes, pull-request comments, or history rewriting.
- Automatic source formatting or replacing deterministic formatters with an LLM.
