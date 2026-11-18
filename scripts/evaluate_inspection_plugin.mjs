// Contract fixture, not an OpenCode server integration test. Execute the real
// transform with an SDK-shaped editor; only Plugin.define is replaced so the
// offline checks and policy generation need neither SDK installation nor a
// running service. This does not model built-in plugin registration order.
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
await plugin.setup({
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
