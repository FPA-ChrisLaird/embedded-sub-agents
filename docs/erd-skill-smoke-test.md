# ERD skill interactive smoke test

## Purpose

Policy-text and installer tests do not establish agent behavior. Use this
read-only interactive check after changing the skill, its permissions, or the
OpenCode version. Never auto-approve permissions to make a smoke test pass.

## Procedure

1. Install with `py -3.15 scripts/install_opencode_agents.py` (or the supported
   Python interpreter on your workstation), then restart OpenCode in an
   unrelated workspace. Do not supply a checkout path initially.
2. Select `embedded-engineer` and ask: "Use erd-knowledge to look up 0x0801.
   Read-only inspection only; no devices, builds, writes, or repository updates."
3. Confirm that the skill loads and asks for the specification checkout path.
   Provide your approved local checkout. Approve only the intended read access
   through OpenCode's permission prompt; if denied, the agent must stop.
4. Confirm it reads the README and source revision, follows the payload reference
   from `erd/0x0___/0x0801.lua` to `erd/0x0___/0x0800.lua`, and cites both files.
   Compare the answer to the current source, not a frozen expected catalogue.
   At the checkout inspected during development, 0x0801 is Sound Theme Request
   with client ownership, while 0x0800 is Current Sound Theme with device
   ownership. The shared payload is a uint8 enum: Default=0, Classical=1,
   Morse Code=2. Sharing the payload must not replace the request's ownership.
5. Ask a follow-up about the same ERD. Confirm the checkout path is reused in
   that session without another conversational path question. Permission
   prompts are separate and must not be bypassed.
6. Confirm the response records the revision and checks source consistency
   before finalizing. Do not update the real specification checkout during
   the test. A controlled revision-change scenario requires a disposable,
   explicitly approved fixture checkout; it is not covered by the basic test.

## Observed validation

- A fresh `opencode debug skill` process outside this repository discovered
  the global skill at `~/.config/opencode/skills/erd-knowledge/SKILL.md`.
- A fresh read-only `opencode run` session loaded that global skill, reused a
  supplied checkout path, and requested external-directory permission. The
  noninteractive runner auto-rejected it; lookup execution was blocked. No
  permission override or alternate access route was used.
- After a session restart, the project skill loaded and a read-only lookup
  reused the previously supplied path. It followed 0x0801's payload reference
  to 0x0800 while preserving client ownership for 0x0801 and device ownership
  for 0x0800, and reported the enum values above with source references.
  The checkout was clean at `5647a7e45bb07fcf9558b718d8630f5aadd47725`;
  HEAD was unchanged on recheck and the inspected files matched HEAD.
- Path-question behavior with no supplied path, separate follow-up reuse,
  and revision-change recovery still require interactive verification. The
  completed lookup used the project skill; global discovery/loading was
  verified separately above. Do not claim broader behavioral coverage.
