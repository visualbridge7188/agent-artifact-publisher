# Agent Artifact Publisher

AI Agent가 작업을 끝낸 뒤, 결과물을 **GitHub + Notion + Google Drive Wiki + 로컬 설치 가이드**까지 한 번에 정리하도록 도와주는 도구입니다.

쉽게 말하면:

> Codex나 Antigravity가 숙제를 끝낸 뒤, 결과물 파일, 설명서, 사용법, 링크 모음을 깔끔하게 제출하게 만드는 정리 도구입니다.

---

## 1. 왜 만들었나요?

AI Agent와 작업하면 결과물이 여기저기 흩어집니다.

예:

- 코드는 GitHub에 있어야 함
- 작업 과정과 사용법은 Wiki에 있어야 함
- Notion에는 “무엇을 만들었는지” 기록해야 함
- 나중에 다시 쓰려면 설치 방법과 실행 방법이 있어야 함

이걸 매번 사람이 직접 정리하면 귀찮고 자주 빠뜨립니다.

그래서 이 도구는 작업 말미에 다음 파일들을 자동으로 만듭니다.

```text
.artifact-publisher/
  artifact-manifest.json   # 전체 결과 기록
  publish-report.md        # 최종 보고서
  install.md               # 설치/사용법
  links.md                 # 링크 모음
  github/pr-body.md        # GitHub PR 본문
  notion/notion-page.md    # Notion에 올릴 내용
```

---

## 2. 무엇을 할 수 있나요?

### 현재 되는 것

- 작업 폴더를 기준으로 결과물 정리
- GitHub PR body 생성
- GitHub 실제 PR 생성
- Notion page 생성 후 read-back 검증
- Google Drive Wiki 폴더에 Markdown 작성 후 read-back 검증
- 로컬 설치/사용 가이드 생성
- MCP-style tool 함수 제공
- CLI fallback 제공
- Codex / Antigravity용 프롬프트 제공

### 아직 개선할 것

- Notion 기존 페이지 자동 검색 후 update 고도화
- 정식 MCP runtime server 연결
- 실제 프로젝트별 GDrive Wiki root 자동 탐색

---

## 3. 설치 방법

이 repo를 받은 뒤:

```bash
uv sync
```

테스트:

```bash
uv run pytest -q
```

정상이라면:

```text
12 passed
```

---

## 4. 제일 쉬운 사용법

현재 폴더의 작업 결과물을 정리하려면:

```bash
uv run python -m agent_artifact_publisher.cli \
  --workdir . \
  --title "내가 만든 결과물 이름" \
  --artifact-type skill \
  --project "프로젝트명" \
  --summary "무엇을 만들었고 왜 필요한지 한 문장" \
  --github pr-body-only \
  --notion dry-run \
  --gdrive-wiki dry-run
```

그러면 `.artifact-publisher/` 폴더가 생깁니다.

---

## 5. GitHub에 실제 PR 만들기

GitHub 토큰이 있어야 합니다.

```bash
export GITHUB_TOKEN="..."
```

실행:

```bash
uv run python -m agent_artifact_publisher.cli \
  --workdir . \
  --title "내 결과물" \
  --artifact-type tool \
  --project "AI Agent Operations" \
  --summary "AI Agent 작업 결과물을 정리하는 도구" \
  --github pr-api \
  --notion dry-run \
  --gdrive-wiki dry-run
```

`gh` CLI가 있으면 `--github pr`도 사용할 수 있습니다.

---

## 6. Notion에 실제 페이지 만들기

Notion 토큰과 DB ID가 필요합니다.

```bash
export NOTION_TOKEN="..."
export NOTION_ARTIFACT_DB_ID="..."
```

실행:

```bash
uv run python -m agent_artifact_publisher.cli \
  --workdir . \
  --title "내 결과물" \
  --artifact-type tool \
  --project "AI Agent Operations" \
  --summary "AI Agent 작업 결과물을 정리하는 도구" \
  --github pr-body-only \
  --notion create \
  --gdrive-wiki dry-run
```

생성 후 Notion page를 다시 읽어서 검증합니다.

---

## 7. Google Drive Wiki에 실제 문서 쓰기

Google Drive가 로컬 폴더처럼 연결되어 있어야 합니다.

예:

```bash
export GDRIVE_WIKI_ROOT="/path/to/GoogleDrive/Wiki"
```

실행:

```bash
GDRIVE_WIKI_ROOT="/path/to/GoogleDrive/Wiki" \
uv run python -m agent_artifact_publisher.cli \
  --workdir . \
  --title "내 결과물" \
  --artifact-type tool \
  --project "AI Agent Operations" \
  --summary "AI Agent 작업 결과물을 정리하는 도구" \
  --github pr-body-only \
  --notion dry-run \
  --gdrive-wiki write
```

작성 후 파일을 다시 읽어서 검증합니다.

---

## 8. Codex / Antigravity에게 시킬 때

`CODEX_ANTIGRAVITY_PROMPT.md` 내용을 작업 말미에 붙여넣으면 됩니다.

요약하면 이렇게 시키면 됩니다.

```text
이 작업 결과물을 Agent Artifact Publisher로 정리/발행해줘.
GitHub, Notion, GDrive Wiki, local install guide까지 만들고,
검증 안 된 것은 완료라고 쓰지 마.
```

---

## 9. MCP-style tool 사용법

Python에서 직접 호출할 수도 있습니다.

```python
from agent_artifact_publisher.mcp.tools import publish_artifact_tool

result = publish_artifact_tool(
    workdir=".",
    title="Demo Skill",
    artifact_type="skill",
    project="AI Agent Operations",
    summary="Demo artifact publishing",
    created_by_agent="codex",
    dry_run=True,
)

print(result)
```

MCP self-test:

```bash
uv run python -m agent_artifact_publisher.mcp.server --self-test
```

정상 출력:

```json
{"tools": ["publish_artifact"], "status": "ok"}
```

---

## 10. 안전 규칙

이 도구는 기본적으로 안전하게 동작합니다.

- 삭제 안 함
- force push 안 함
- Notion taxonomy 새 옵션 생성 안 함
- 검증 실패하면 완료라고 안 함
- 일부만 성공하면 `partial`로 기록

---

## 11. 실제 검증 결과

이 repo는 실제로 아래를 검증했습니다.

- GitHub repo 승격: 완료
- GitHub PR 생성: 완료
- Notion page 생성/read-back: 완료
- Wiki local-root write/read-back: 완료
- pytest: `12 passed`

---

## 12. 폴더 구조

```text
agent_artifact_publisher/
  cli.py                  # CLI fallback
  config.py               # 설정/env 처리
  model.py                # manifest 데이터 모델
  scanner.py              # 작업 폴더 스캔
  renderer.py             # 문서 생성
  orchestrator.py         # 전체 실행 흐름
  mcp/tools.py            # Agent가 부를 tool 함수
  mcp/server.py           # MCP self-test shim
  publishers/github.py    # GitHub 발행
  publishers/notion.py    # Notion 발행
  publishers/gdrive_wiki.py # GDrive Wiki 발행
  playbook/AGENT_PLAYBOOK.md
```

---

## 13. 한 줄 요약

> AI Agent가 만든 결과물을 “제출 가능한 상태”로 정리해주는 작업 마감 도구입니다.
