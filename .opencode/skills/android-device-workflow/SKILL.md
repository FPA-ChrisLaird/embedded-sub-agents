---
name: android-device-workflow
description: Use for Android APK builds, ADB device discovery, APK transfers or installation, log capture, and installed-app launches. Loads the primary-only build and device safeguards; do not load for non-Android work.
---

# Android Device Workflow

Only the primary embedded engineer may execute this workflow. Analysis
subagents must not run ADB or access devices. Loading this skill is not human
authorization or shell permission approval. If another agent loads it, stop
device execution and return the task to the primary.

## Local APK builds

The primary may build APKs using inspected, approval-gated local build tasks,
such as `gradlew assembleDebug` or a project-documented non-release variant.
Inspect the project's build instructions, wrapper, task dependencies, and
artifact destination before running an unfamiliar command. Explain expected
outputs and any dependency downloads or generated-file changes. Obtain shell
permission approval; do not auto-approve build commands or bypass plugin denials.

Use the existing project toolchain and conventions. Do not expose signing keys,
credentials, or unrelated private data. Firmware flashing, package/release
targets, publishing, and distribution remain prohibited; do not substitute a
release build when the requested variant is unavailable. Local APK compilation
does not authorize device access, installation, or launch. Build cleanup still
requires explicit human approval and inspection confirming that only
regenerable build artifacts are removed.

## Allowed scope and authorization

With explicit human authorization and shell permission approval, the primary
may use ADB to list devices, inspect APK locations, pull or push APKs and log
files, install or update APKs, and read or capture logs with `adb logcat`.
APK installation is application deployment, not permission to flash firmware
or run package/release build targets. Confirm the intended device serial and
use `adb -s <serial>` for device operations. Confirm source/destination paths
before transfers and explain replacement effects before writes or installs.

An explicit human authorization may cover a defined APK/log task on a named
device for the current session, including agreed paths and replacement effects.
Record that scope once and reuse it for subsequent in-scope steps without
repeated conversational confirmation. Reconfirm if the device, task, transfer
paths, or replacement effects change, or if authorization is revoked or unclear.
This does not waive shell permission prompts or authorize additional operations.

## Installed-app launches

Use only narrowly scoped `adb shell` commands needed to locate/read these
files, inspect APK metadata, or launch the approved installed app. Launching
requires explicit authorization covering the app and device; confirm its
package/activity from APK metadata or a narrowly scoped read-only activity
resolution query, then use
`adb -s <serial> shell am start -n <package>/<activity>` without unapproved
intent arguments. Installing an APK alone does not authorize launching it.
Task-scoped authorization may include repeated launches of that same app.
Explain that launching executes application code and may affect app state or
connected equipment; obtain confirmation of those effects before launching.

## Boundaries

This is not authorization for arbitrary shell execution, root/remount, reboot,
uninstall, app-data/log clearing, partition writes, UI automation, or other
device operations. Do not collect credentials or unrelated private data.
Never flash or program firmware, or run package or release targets.
ADB stays approval-gated; do not bypass plugin denials with wrappers or
alternate syntax. Keep logs and metadata bounded to the approved task; do not
collect unrelated device data or paste entire captures into context by default.
