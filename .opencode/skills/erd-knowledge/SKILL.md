---
name: erd-knowledge
description: Use for GEA Entity Reference Designator (ERD) ID/name lookup, payload interpretation, ownership, or Appliance API feature membership using the local ERD specification checkout. Load only for ERD-related work, not general embedded tasks.
---

# ERD Knowledge

## Scope and source

This is a primary-agent, read-only lookup workflow, not a device-control skill.
It does not authorize ERD writes, device access, source modifications, protocol
changes, builds, publishing, or permission changes. Analysis subagents must not
use it to bypass their external-directory or skill restrictions. The primary
may supply bounded excerpts to a specialist without expanding its permissions.

On first use, ask the user: "Where is your local
documentation.erd-specification checkout?" If the user already supplied its
path in the current session, reuse it without asking again. Confirm the
directory contains the expected README and `erd/` definitions before relying
on it. Remember the confirmed path only for the current session; do not write
machine-specific paths into the shared skill or configuration. If absent or
access is denied, ask for an approved checkout; do not silently clone, fetch,
or substitute an online copy. Never bypass an external-directory denial.
Do not copy the full catalogue into this skill or the working repository.

Read the checkout's `README.md` for current conventions. Record its HEAD revision
and relevant local modifications using permitted read-only Git inspection.
Never assume that the latest checkout matches the target firmware contract.
Identify product, firmware/spec revision, and hosting device when material;
state what is unknown rather than inventing a match.

Before finalizing, recheck HEAD and relevant local modifications and verify
the source files used have not changed during the investigation. If the
checkout changed, reread affected definitions and dependencies and redo the
affected interpretation, or report that a consistent result is blocked.
Do not silently mix definitions from different revisions. Weekly checkout
updates require no skill reinstall; changes to repository structure or DSL
conventions may require updating this workflow.

## Targeted lookup

1. Normalize an ID to four hex digits, e.g. `0x0801`. Definitions are under
   `erd/<first-hex-digit-block>/<ID>.lua`, e.g. `erd/0x0___/0x0801.lua`.
   For a name lookup, search within `erd/` and inspect the candidate definition.
   Prefer an existing, fresh graph if available; otherwise use targeted file
   reads/searches. This checkout need not be indexed to perform a text lookup.
2. Read the entire definition and follow every relevant `require` or prototype
   reference, including shared types under `types/` and referenced ERD modules.
   Preserve the selected ERD's own name, description, `data_owner`/`operations`,
   and update metadata; sharing `.data` does not share ownership or semantics.
   Resolve nested structs, arrays, enums, bitfields, scaling, units, sentinel
   values, and descriptions before interpreting a value. Do not execute Lua
   modules or build scripts merely to inspect a definition.
3. Use `appliance-api/<product-family>.lua` for feature membership and follow
   referenced feature definitions. A definition or feature listing alone does
   not prove that the target device implements or advertises it. Check target
   firmware support/advertisement when making such claims.
4. `artifacts/erd_definitions.json` and `artifacts/appliance_api.json` are
   generated conveniences. Check freshness against Lua sources; if provenance
   is unknown or they disagree, report the discrepancy rather than silently
   treating generated data as the deployed contract. Do not regenerate them.

## Interpretation guardrails

- The README defines public IDs as `0x0000–0xDFFF`, service as
  `0xE000–0xEFFF`, and private as `0xF000–0xFFFF`. This repository documents
  public ERDs; service/private meanings may vary by device or firmware release.
  For those, use the relevant product definitions and version evidence. An
  absent file is not proof that an ERD is invalid or unsupported.
- `data_owner = 'client'` denotes request data consumed by the device;
  `'device'` denotes status data; `'shared'` denotes legacy shared ownership.
  Read the current README's mapping to `operations`. Ownership is not access
  authorization, and a request is not proof of acceptance or completed action.
- Do not infer wire byte order, signedness, offsets, bit order, padding, units,
  or scaling from C familiarity or a name. The README requires no implicit
  padding; use the actual DSL/type definitions and transport contract to derive
  layout. Mark any unverified encoding property explicitly as unknown.
- `update_class` describes expected update behavior, not enforced delivery or
  event ordering. Inspect `local_only`, `telemetry_only`, feature advertisement,
  and relevant policy before asserting cloud visibility or notification rates.
- For packets/captures, use `decode-gea-comms` if available for framing,
  escaping, CRC, and transport decoding; keep that separate from ERD payload
  interpretation. Do not assume transport details from this lookup skill.
- If a task changes an externally encoded representation, follow the primary's
  mandatory quality-reviewer delegation policy. This knowledge skill does not
  replace compatibility, persistence, lifecycle, or writer analysis.

## Output and context budget

Return only the relevant ERD ID/name, source revision and paths/line references,
resolved payload layout and metadata, applicable product/version evidence, and
the requested decoded value or feature result. For numeric decoding, show the
input bytes, verified encoding assumptions, calculation, units, and unknowns.
Distinguish documented facts from hypotheses and runtime behavior. Cite shared
definitions as well as the selected ERD. Keep searches and excerpts bounded;
do not load the complete catalogue or unrelated product families into context.
