import type { Config, Plugin } from "@opencode-ai/plugin"

type PermissionAction = "allow" | "ask" | "deny"
type BashPermissions = Record<string, PermissionAction>
type AgentPermission = {
  bash?: BashPermissions | PermissionAction
}
type AgentConfig = {
  permission?: AgentPermission
}
type EmbeddedConfig = Config & {
  agent?: Record<string, AgentConfig | undefined>
}

const TARGET_AGENTS = [
  "embedded-engineer",
  "embedded-architecture-analyst",
  "embedded-c-quality-reviewer",
  "embedded-build-analyzer",
] as const

const AGENT_DEFAULT_BASH_PERMISSIONS: Record<
  (typeof TARGET_AGENTS)[number],
  BashPermissions
> = {
  "embedded-engineer": { "*": "ask" },
  "embedded-architecture-analyst": { "*": "deny" },
  "embedded-c-quality-reviewer": { "*": "deny" },
  "embedded-build-analyzer": { "*": "deny" },
}

const EMBEDDED_ENGINEER_SAFETY_DENIALS: BashPermissions = {
  "*flash*": "deny",
  "*program*": "deny",
  "*openocd*": "deny",
  "*jlink*": "deny",
  "*pyocd*": "deny",
  "*st-flash*": "deny",
  "*dfu-util*": "deny",
  "*avrdude*": "deny",
  "*nrfjprog*": "deny",
  "* clean*": "deny",
  "* package*": "deny",
  "* release*": "deny",
}

const GITHUB_READ_PERMISSIONS: BashPermissions = {
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

const GIT_INSPECTION_PERMISSIONS: BashPermissions = {
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

const GIT_INSPECTION_DENIALS: BashPermissions = {
  "git * --output*": "deny",
  "git * --ext-diff*": "deny",
  "git * --textconv*": "deny",
  "git * --open-files-in-pager*": "deny",
}

const SHELL_COMPOSITION_DENIALS: BashPermissions = {
  "*&&*": "deny",
  "*||*": "deny",
  "*;*": "deny",
  "*|*": "deny",
}

function getApiMutationGuards(action: PermissionAction): BashPermissions {
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

const GITHUB_GRAPHQL_QUERY_PERMISSIONS: BashPermissions = {
  "gh api graphql * -f*": "allow",
  "gh api graphql * -F*": "allow",
  "gh api graphql * --raw-field*": "allow",
  "gh api graphql * --field*": "allow",
}

function getGraphqlMutationGuards(action: PermissionAction): BashPermissions {
  return {
    "gh api graphql *@*": action,
    "gh api graphql *mutation*": action,
  }
}

function getBashPermissions(
  config: EmbeddedConfig,
  agentName: (typeof TARGET_AGENTS)[number],
): BashPermissions {
  const agent = config.agent?.[agentName]

  if (agent === undefined || typeof agent !== "object") {
    throw new Error(`Expected embedded agent '${agentName}' to be configured`)
  }

  if (agent.permission === undefined || typeof agent.permission !== "object") {
    agent.permission = {}
  }

  const bash = agent.permission.bash

  if (bash === undefined) {
    agent.permission.bash = { ...AGENT_DEFAULT_BASH_PERMISSIONS[agentName] }
  } else if (typeof bash === "string") {
    agent.permission.bash = { "*": bash }
  }

  return agent.permission.bash as BashPermissions
}

const plugin: Plugin = async () => ({
  config: async (config) => {
    for (const agentName of TARGET_AGENTS) {
      const permissions = getBashPermissions(config as EmbeddedConfig, agentName)
      const mutationAction =
        agentName === "embedded-engineer" ? "ask" : "deny"

      Object.assign(permissions, GITHUB_READ_PERMISSIONS)
      Object.assign(permissions, GIT_INSPECTION_PERMISSIONS)
      Object.assign(permissions, getApiMutationGuards(mutationAction))
      Object.assign(permissions, GITHUB_GRAPHQL_QUERY_PERMISSIONS)
      Object.assign(permissions, getGraphqlMutationGuards(mutationAction))
      Object.assign(permissions, GIT_INSPECTION_DENIALS)
      Object.assign(permissions, SHELL_COMPOSITION_DENIALS)

      if (agentName === "embedded-engineer") {
        Object.assign(permissions, EMBEDDED_ENGINEER_SAFETY_DENIALS)
      }
    }
  },
})

export default plugin
