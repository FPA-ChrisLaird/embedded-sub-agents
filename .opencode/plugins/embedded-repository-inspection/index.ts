import { Plugin } from "@opencode/plugin"

type PermissionEffect = "allow" | "ask" | "deny"
type ShellPermissions = Record<string, PermissionEffect>
type ShellRule = {
  action: "shell"
  resource: string
  effect: PermissionEffect
}

const TARGET_AGENTS = [
  "embedded-engineer",
  "embedded-architecture-analyst",
  "embedded-c-quality-reviewer",
  "embedded-build-analyzer",
] as const

const AGENT_DEFAULT_SHELL_EFFECT: Record<
  (typeof TARGET_AGENTS)[number],
  PermissionEffect
> = {
  "embedded-engineer": "ask",
  "embedded-architecture-analyst": "deny",
  "embedded-c-quality-reviewer": "deny",
  "embedded-build-analyzer": "deny",
}

const EMBEDDED_ENGINEER_SAFETY_DENIALS: ShellPermissions = {
  "*flash*": "deny",
  "*program*": "deny",
  "*openocd*": "deny",
  "*jlink*": "deny",
  "*pyocd*": "deny",
  "*st-flash*": "deny",
  "*dfu-util*": "deny",
  "*avrdude*": "deny",
  "*nrfjprog*": "deny",
  "* package*": "deny",
  "* release*": "deny",
}

const GITHUB_READ_PERMISSIONS: ShellPermissions = {
  "gh auth status*": "allow",
  "gh repo view*": "allow",
  "gh pr view*": "allow",
  "gh pr list*": "allow",
  "gh pr status*": "allow",
  "gh pr checks*": "allow",
  "gh pr diff*": "allow",
  "gh issue view*": "allow",
  "gh issue list*": "allow",
  "gh run view*": "allow",
  "gh run list*": "allow",
  "gh run watch*": "allow",
  "gh workflow view*": "allow",
  "gh workflow list*": "allow",
  "gh api repos/*": "allow",
  "gh api graphql *": "allow",
}

const GIT_INSPECTION_PERMISSIONS: ShellPermissions = {
  "git --no-optional-locks --no-pager status*": "allow",
  "git --no-pager diff --no-ext-diff --no-textconv": "allow",
  "git --no-pager diff --no-ext-diff --no-textconv *": "allow",
  "git --no-pager show --no-ext-diff --no-textconv": "allow",
  "git --no-pager show --no-ext-diff --no-textconv *": "allow",
  "git --no-pager branch --show-current": "allow",
  "git --no-pager branch": "allow",
  "git --no-pager branch --list": "allow",
  "git --no-pager branch --all": "allow",
  "git --no-pager branch --remotes": "allow",
  "git --no-pager branch -a": "allow",
  "git --no-pager branch -r": "allow",
  "git rev-parse *": "allow",
  "git --no-pager log --no-ext-diff --no-textconv": "allow",
  "git --no-pager log --no-ext-diff --no-textconv *": "allow",
  "git --no-pager reflog": "allow",
  "git --no-pager reflog show*": "allow",
  "git merge-base *": "allow",
  "git describe *": "allow",
  "git name-rev *": "allow",
  "git --no-pager tag": "allow",
  "git --no-pager tag --list*": "allow",
  "git worktree list*": "allow",
  "git stash list*": "allow",
  "git submodule status*": "allow",
  "git sparse-checkout list": "allow",
  "git remote": "allow",
  "git remote -v": "allow",
  "git remote get-url *": "allow",
  "git config --get *": "allow",
  "git config --get-all *": "allow",
  "git config --get-regexp *": "allow",
  "git config --list": "allow",
  "git config --show-origin --list": "allow",
  "git ls-files*": "allow",
  "git ls-tree *": "allow",
  "git cat-file -e *": "allow",
  "git cat-file -t *": "allow",
  "git cat-file -s *": "allow",
  "git show-ref*": "allow",
  "git for-each-ref*": "allow",
  "git rev-list *": "allow",
  "git check-ignore *": "allow",
  "git check-attr *": "allow",
  "git --no-pager blame *": "allow",
  "git --no-pager shortlog*": "allow",
}

const GIT_INSPECTION_DENIALS: ShellPermissions = {
  "git * --output*": "deny",
  "git * --ext-diff*": "deny",
  "git * --textconv*": "deny",
  "git * --open-files-in-pager*": "deny",
}

// Retain the resource-level denials as a fallback for matching resources;
// the hook below handles separators between resources.
const SHELL_COMPOSITION_DENIALS: ShellPermissions = {
  "*&&*": "deny",
  "*||*": "deny",
  "*;*": "deny",
  "*|*": "deny",
}

function getApiMutationGuards(action: PermissionEffect): ShellPermissions {
  return {
    "gh api * -X*": action,
    "gh api * -X *": action,
    "gh api * --method=*": action,
    "gh api * --method *": action,
    "gh api * -f*": action,
    "gh api * -f *": action,
    "gh api * -F*": action,
    "gh api * -F *": action,
    "gh api * --raw-field=*": action,
    "gh api * --raw-field *": action,
    "gh api * --field=*": action,
    "gh api * --field *": action,
    "gh api * --input=*": action,
    "gh api * --input *": action,
  }
}

const GITHUB_GRAPHQL_QUERY_PERMISSIONS: ShellPermissions = {
  "gh api graphql * -f*": "allow",
  "gh api graphql * -F*": "allow",
  "gh api graphql * --raw-field*": "allow",
  "gh api graphql * --field*": "allow",
}

function getGraphqlMutationGuards(action: PermissionEffect): ShellPermissions {
  return {
    "gh api graphql *@*": action,
    "gh api graphql *mutation*": action,
  }
}

function shellRules(permissions: ShellPermissions): ShellRule[] {
  return Object.entries(permissions).map(([resource, effect]) => ({
    action: "shell",
    resource,
    effect,
  }))
}

// Permission rules see scanner-produced resources, not the original input.
// Inspect the whole call separately. Reject separator characters even in
// quoted arguments rather than implement a second, shell-specific parser.
const SHELL_SEPARATORS = /[&|;\r\n]/

export default Plugin.define({
  id: "embedded-repository-inspection",
  async setup(ctx) {
    await ctx.tool.hook("execute.before", (event) => {
      if (
        event.tool !== "shell" ||
        !TARGET_AGENTS.some((name) => name === event.agent)
      ) {
        return
      }

      const input = event.input as { command?: unknown } | null | undefined
      if (typeof input?.command !== "string") {
        throw new Error("A shell call must provide a command string.")
      }
      if (SHELL_SEPARATORS.test(input.command)) {
        throw new Error(
          "Shell composition is disabled. Run one command at a time without &, |, semicolons, or line breaks.",
        )
      }
    })

    await ctx.agent.transform((editor) => {
      for (const agentName of TARGET_AGENTS) {
        // Disabled/absent agents must stay absent, including in global installs.
        if (!editor.get(agentName)) continue

        editor.update(agentName, (agent) => {
          if (!agent.permissions.some((rule) => rule.action === "shell")) {
            agent.permissions.push({
              action: "shell",
              resource: "*",
              effect: AGENT_DEFAULT_SHELL_EFFECT[agentName],
            })
          }

          const mutationAction =
            agentName === "embedded-engineer" ? "ask" : "deny"

          // V2 uses last-match-wins rules. Keep broad allows before guards,
          // and GraphQL query exceptions before GraphQL mutation guards.
          agent.permissions.push(
            ...shellRules(GITHUB_READ_PERMISSIONS),
            ...shellRules(GIT_INSPECTION_PERMISSIONS),
            ...shellRules(getApiMutationGuards(mutationAction)),
            ...shellRules(GITHUB_GRAPHQL_QUERY_PERMISSIONS),
            ...shellRules(getGraphqlMutationGuards(mutationAction)),
            ...shellRules(GIT_INSPECTION_DENIALS),
            ...shellRules(SHELL_COMPOSITION_DENIALS),
          )

          if (agentName === "embedded-engineer") {
            agent.permissions.push(...shellRules(EMBEDDED_ENGINEER_SAFETY_DENIALS))
          }
        })
      }
    })
  },
})
