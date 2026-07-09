# Codex / Antigravity Artifact Publish Prompt

작업 말미에 아래 프롬프트를 로컬 Agent에게 붙여넣는다.

```text
이 작업 결과물을 Agent Artifact Publisher로 정리/발행해줘.

실행 주체는 너다. Hermes에게 넘기지 마라.

대상:
- 현재 workdir의 AI 작업 산출물
- artifact type: skill/tool/script/app/workflow 중 맞는 값으로 판단
- project: 사용자가 말한 프로젝트명 또는 repo/폴더 맥락으로 추론

필수 산출물:
1. `.artifact-publisher/artifact-manifest.json`
2. `.artifact-publisher/publish-report.md`
3. `.artifact-publisher/install.md`
4. `.artifact-publisher/links.md`
5. `.artifact-publisher/github/pr-body.md`
6. `.artifact-publisher/notion/notion-page.md`
7. GDrive Wiki Markdown 문서 또는 실패 상태

발행 규칙:
- GitHub는 기본 `pr-body-only`; 사용자가 허용하면 `--github pr`로 실제 PR 생성.
- Notion은 기본 `dry-run`; 토큰/DB가 있고 사용자가 허용하면 `--notion create` 또는 `--notion update`.
- GDrive Wiki는 `GDRIVE_WIKI_ROOT`가 있으면 `--gdrive-wiki write`.
- 새 Notion taxonomy/status option 생성 금지.
- 삭제/archive/force push 금지.
- read-back 검증 없이 완료라고 쓰지 마라.
- 실패한 target은 `partial`로 보고하고 복구 액션을 적어라.

실행 예시:

```bash
uv run python -m agent_artifact_publisher.cli \
  --workdir . \
  --title "작업 결과물 이름" \
  --artifact-type skill \
  --project "프로젝트명" \
  --summary "무엇을 만들었고 왜 필요한지 한 문장" \
  --github pr-body-only \
  --notion dry-run \
  --gdrive-wiki dry-run
```

GDrive Wiki까지 실제 쓰기:

```bash
GDRIVE_WIKI_ROOT="/path/to/GoogleDrive/Wiki" \
uv run python -m agent_artifact_publisher.cli \
  --workdir . \
  --title "작업 결과물 이름" \
  --artifact-type skill \
  --project "프로젝트명" \
  --summary "무엇을 만들었고 왜 필요한지 한 문장" \
  --github pr-body-only \
  --notion dry-run \
  --gdrive-wiki write
```

최종 답변은 아래만:
- 상태: 완료/부분완료/차단
- GitHub: 링크 또는 pr-body 경로
- Notion: 링크 또는 notion-page 경로
- GDrive Wiki: 링크/경로 또는 실패 이유
- Local install: install.md 경로
- Manifest: artifact-manifest.json 경로
- 다음 액션 1개
```
