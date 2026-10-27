# CampusPilot development instructions

## Read before working

- [System inventory](docs/CAMPUSPILOT_SYSTEM_STATUS.md): architecture and dated evidence.
- [Development orchestrator](docs/agents/ORCHESTRATOR.md): roles, routing, safety and Definition of Done.
- Applicable nested instructions, especially [frontend instructions](frontend/AGENTS.md).

Verify current Git state and source; documentation is not proof of current behavior.
Preserve existing staged, unstaged, untracked and unrelated work. Never discard or
overwrite it to make a task easier. Keep each change within the user's scope.

## Lead and specialists

The primary session is the Lead Orchestrator. Project specialists are defined in
.codex/agents/. When native discovery supports them, delegate appropriate bounded
tasks to campuspilot_ai_rag, campuspilot_backend, campuspilot_frontend,
campuspilot_security, campuspilot_testing, or campuspilot_devops.

Use parallel agents only for independent work. Assign explicit file ownership:
one writer per file, reviewers read-only by default, shared-contract edits serialized.
With uncommitted work, prefer read-only delegation. If named-agent dispatch is not
available, disclose that limitation and use the corresponding role instructions
in a supported child task or work sequentially. Never claim configuration was
loaded merely because a task was given the same name.

## Approval and verification

Do not use delegation to bypass approval. Commits, pushes, PR creation, merges,
deployments, CI changes, shared-schema changes, package/plugin/skill installation,
production access, and paid model calls require explicit scoped user approval.
Respect Brian's backend, Josiah's frontend, John Paul's integration, and Cassie's
DevOps ownership. Do not expose credentials or private records in output or prompts.

Verify specialist findings against source and test evidence. Report exact files,
checks executed, results, limitations and final Git status. Distinguish mocked
success, live-model success, hosted CI, and deployment. Do not claim unrun checks
passed. Keep development-agent coordination separate from the student-facing AI.

Use existing skills when applicable and read their instructions before use. The
user's restrictions override skill defaults; skill availability is not permission
to commit, publish, install or deploy.
