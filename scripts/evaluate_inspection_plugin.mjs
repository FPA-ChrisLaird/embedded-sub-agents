// Contract fixture, not an OpenCode server integration test. Execute the real
// transform and pre-execution hook with SDK-shaped fixtures. Replacing
// Plugin.define keeps these checks and generation offline. This does not
// emulate the shell scanner or built-in plugin registration order.
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { stripTypeScriptTypes } from "node:module"

const source = readFileSync(process.argv[2], "utf8")
const sdkImport = 'import { Plugin } from "@opencode/plugin"'
assert.ok(source.includes(sdkImport))
const code = stripTypeScriptTypes(source.replace(
  sdkImport,
  "const Plugin = { define: (definition) => definition }",
))
const { default: plugin } = await import(
  `data:text/javascript;base64,${Buffer.from(code).toString("base64")}`
)
assert.equal(plugin.id, "embedded-repository-inspection")
const agents = JSON.parse(readFileSync(0, "utf8"))
let transform
let registrations = 0
let beforeExecute
await plugin.setup({
  tool: {
    async hook(name, callback) {
      assert.equal(name, "execute.before")
      assert.equal(typeof callback, "function")
      assert.equal(beforeExecute, undefined, "register only one pre-execution hook")
      beforeExecute = callback
      return { async dispose() {} }
    },
  },
  agent: {
    async transform(callback) {
      assert.equal(typeof callback, "function")
      transform = callback
      registrations++
      return { async dispose() {} }
    },
  },
})
assert.equal(registrations, 1)

if (process.argv.includes("--check-shell-hook")) {
  assert.equal(typeof beforeExecute, "function")
  const firstCommand = "git rev-parse HEAD"
  const secondCommand = "git ls-files"

  for (const agent of Object.keys(agents)) {
    let runs = 0
    async function run(tool, input) {
      const event = { tool, agent, input }
      const original = structuredClone(event)
      await beforeExecute(event)
      assert.deepEqual(event, original, "the guard must not rewrite allowed inputs")
      runs++ // Fake executor: these fixtures never start a shell.
    }

    await run("shell", { command: firstCommand })
    await run("shell", { command: secondCommand })
    await run("read", { filePath: "docs/test;file.md" })
    for (const separator of [" && ", " || ", "; ", " | ", " & ", "\n", "\r\n"]) {
      await assert.rejects(
        run("shell", { command: firstCommand + separator + secondCommand }),
        /Shell composition is disabled/,
      )
    }
    await assert.rejects(
      run("shell", { command: 'git ls-files "a;b"' }),
      /Shell composition is disabled/,
    )
    for (const input of [undefined, null, {}, { command: 42 }]) {
      await assert.rejects(run("shell", input), /provide a command string/)
    }
    assert.equal(runs, 3, `a rejected ${agent} input must not reach execution`)
  }

  // The shared plugin can be installed globally; don't restrict other roles.
  await beforeExecute({
    tool: "shell",
    agent: "build",
    input: { command: firstCommand + " && " + secondCommand },
  })
}

function replay() {
  const result = structuredClone(agents)
  const returned = transform({
    get(id) { return result[id] },
    update(id, update) {
      assert.ok(result[id], `must not recreate absent agent ${id}`)
      update(result[id])
    },
  })
  assert.equal(returned, undefined, "transforms must be synchronous")
  return result
}
const first = replay()
assert.deepEqual(replay(), first, "fresh-state replay must be deterministic")
process.stdout.write(JSON.stringify(first))
