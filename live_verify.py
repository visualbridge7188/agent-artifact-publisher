#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path('/opt/data/work-logs/agent-artifact-publisher-impl')
ENV = Path('/opt/data/.env')
RESULT = ROOT / '.artifact-publisher' / 'live-verification.json'
RESULT.parent.mkdir(parents=True, exist_ok=True)


def load_env():
    if ENV.exists():
        for line in ENV.read_text(encoding='utf-8', errors='ignore').splitlines():
            if not line or line.lstrip().startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"\''))


def api(method, url, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, json.loads(raw) if raw else {}
    except Exception as e:
        detail = getattr(e, 'read', lambda: b'')()
        return getattr(e, 'code', 0) or 0, {'message': detail.decode(errors='ignore') if detail else str(e)}


def notion(method, path, token, payload=None):
    data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    req = urllib.request.Request('https://api.notion.com/v1/' + path, data=data, method=method, headers={
        'Authorization': 'Bearer ' + token,
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, json.loads(raw) if raw else {}
    except Exception as e:
        detail = getattr(e, 'read', lambda: b'')()
        return getattr(e, 'code', 0) or 0, {'message': detail.decode(errors='ignore') if detail else str(e)}


def run(cmd, cwd=ROOT, env=None):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, env=merged)
    return {'cmd': cmd, 'returncode': p.returncode, 'stdout': p.stdout.strip(), 'stderr': p.stderr.strip()}


def main():
    load_env()
    out = {'github': {}, 'notion': {}, 'gdrive': {}}
    ts = time.strftime('%Y%m%d%H%M%S')

    # GitHub live test: create/ensure private test repo, then run artifact publisher pr-api against it.
    gh_token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if gh_token:
        st, user = api('GET', 'https://api.github.com/user', gh_token)
        out['github']['user_status'] = st
        login = user.get('login')
        repo_name = 'agent-artifact-publisher-live-test'
        st, repo = api('GET', f'https://api.github.com/repos/{login}/{repo_name}', gh_token)
        if st == 404:
            st, repo = api('POST', 'https://api.github.com/user/repos', gh_token, {'name': repo_name, 'private': True, 'auto_init': True, 'description': 'Live verification repo for Agent Artifact Publisher'})
        out['github']['repo_status'] = st
        out['github']['repo_url'] = repo.get('html_url')
        if st in {200, 201}:
            live_dir = ROOT / 'live-github-workdir'
            live_dir.mkdir(exist_ok=True)
            (live_dir / 'README.md').write_text('# Live GitHub Workdir\n', encoding='utf-8')
            if not (live_dir / '.git').exists():
                run(['git', 'init'], cwd=live_dir)
            run(['git', 'remote', 'remove', 'origin'], cwd=live_dir)
            run(['git', 'remote', 'add', 'origin', repo['clone_url']], cwd=live_dir)
            env={'GITHUB_TOKEN': gh_token}
            res = run(['uv','run','python','-m','agent_artifact_publisher.cli','--workdir',str(live_dir),'--title',f'Live GitHub Verification {ts}','--artifact-type','tool','--project','AI Agent Operations','--summary','Live verification of GitHub PR API publishing.','--github','pr-api','--notion','dry-run','--gdrive-wiki','dry-run'], env=env)
            out['github']['publisher_run'] = {'returncode': res['returncode'], 'stdout': res['stdout'], 'stderr_tail': res['stderr'][-500:]}
            manifest_path = live_dir / '.artifact-publisher' / 'artifact-manifest.json'
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text())
                out['github']['manifest_status'] = manifest.get('status')
                for target in manifest.get('targets', []):
                    if target.get('target') == 'github':
                        out['github']['pr_url'] = target.get('url_or_path')
                        out['github']['target_status'] = target.get('status')
                        out['github']['target_error'] = target.get('error')
    else:
        out['github']['blocked'] = 'missing GITHUB_TOKEN/GH_TOKEN'

    # Notion live test against Notes DB.
    notion_token = os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')
    notes_db = os.environ.get('NOTION_ARTIFACT_DB_ID') or '6375cdc67fc74764bda06eb61572df0f'
    if notion_token:
        st, db = notion('GET', f'databases/{notes_db}', notion_token)
        out['notion']['db_status'] = st
        out['notion']['db_title'] = ''.join(t.get('plain_text','') for t in db.get('title', [])) if st == 200 else ''
        env={'NOTION_TOKEN': notion_token, 'NOTION_ARTIFACT_DB_ID': notes_db}
        res = run(['uv','run','python','-m','agent_artifact_publisher.cli','--workdir',str(ROOT),'--title',f'Agent Artifact Publisher Live Notion Verification {ts}','--artifact-type','tool','--project','AI Agent Operations','--summary','Live verification of Notion page creation and read-back.','--github','pr-body-only','--notion','create','--gdrive-wiki','dry-run'], env=env)
        out['notion']['publisher_run'] = {'returncode': res['returncode'], 'stdout': res['stdout'], 'stderr_tail': res['stderr'][-500:]}
        manifest_path = ROOT / '.artifact-publisher' / 'artifact-manifest.json'
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            for target in manifest.get('targets', []):
                if target.get('target') == 'notion':
                    out['notion']['page_url'] = target.get('url_or_path')
                    out['notion']['target_status'] = target.get('status')
                    out['notion']['target_error'] = target.get('error')
    else:
        out['notion']['blocked'] = 'missing NOTION_TOKEN/NOTION_API_KEY'

    # GDrive Wiki live local-root test. Use /opt/data/wiki if no mounted Google Drive root is configured.
    wiki_root = Path(os.environ.get('GDRIVE_WIKI_ROOT') or '/opt/data/wiki')
    res = run(['uv','run','python','-m','agent_artifact_publisher.cli','--workdir',str(ROOT),'--title',f'Agent Artifact Publisher Live Wiki Verification {ts}','--artifact-type','tool','--project','AI Agent Operations','--summary','Live verification of GDrive Wiki local-root write and read-back.','--github','pr-body-only','--notion','dry-run','--gdrive-wiki','write'], env={'GDRIVE_WIKI_ROOT': str(wiki_root)})
    out['gdrive']['root'] = str(wiki_root)
    out['gdrive']['publisher_run'] = {'returncode': res['returncode'], 'stdout': res['stdout'], 'stderr_tail': res['stderr'][-500:]}
    manifest_path = ROOT / '.artifact-publisher' / 'artifact-manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for target in manifest.get('targets', []):
            if target.get('target') == 'gdrive_wiki':
                out['gdrive']['wiki_path'] = target.get('url_or_path')
                out['gdrive']['target_status'] = target.get('status')
                out['gdrive']['target_error'] = target.get('error')
                p = Path(target.get('url_or_path') or '')
                out['gdrive']['readback_exists'] = p.exists()
                out['gdrive']['readback_has_title'] = p.exists() and 'Agent Artifact Publisher Live Wiki Verification' in p.read_text(encoding='utf-8')

    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(RESULT)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
