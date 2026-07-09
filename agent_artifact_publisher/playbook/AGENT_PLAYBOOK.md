# Agent Artifact Publisher Playbook

Use when finishing AI-agent work that must be preserved in GitHub, Notion, and GDrive Wiki.

## Required Flow

1. Inspect workdir and identify artifact type.
2. Generate usage, install, smoke-test, uninstall, and rollback information.
3. Prepare GitHub publish output.
4. Write or prepare GDrive Wiki guide.
5. Create or prepare Notion ledger page.
6. Verify all targets by read-back.
7. Return only links, status, and next action.

## Completion Gate

Do not claim complete unless `artifact-manifest.json`, `publish-report.md`, `install.md`, and `links.md` exist and every requested target has verified, partial, or failed status.

## Safety Rules

- Do not create Notion taxonomy/status options.
- Do not delete, archive, or force-push.
- Do not mark unverified writes as complete.
- If a target fails, report `partial` and include the recovery action.
