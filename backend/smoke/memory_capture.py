# -*- coding: utf-8 -*-
"""Best-effort bridge from Smoke Center results into Little C local memory."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable


DEFAULT_MEMORY_SCRIPT = Path(r"C:\Users\Administrator\Documents\Codex\2026-05-09\new-chat-3\scripts\memory_system.py")
DEFAULT_PROJECT_KEY = "intelligent-data-platform"


def _normalize_tags(tags: Iterable[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags or []:
        item = str(tag).strip()
        if not item:
            continue
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(item)
    return normalized


def locate_memory_script() -> Path | None:
    configured = os.environ.get("LITTLE_C_MEMORY_SCRIPT", "").strip()
    candidates = [Path(configured)] if configured else []
    candidates.append(DEFAULT_MEMORY_SCRIPT)
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return None


def _run(script_path: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        [sys.executable, str(script_path), *arguments],
        capture_output=True,
        text=False,
        check=True,
    )
    stdout = _decode_output(process.stdout)
    stderr = _decode_output(process.stderr)
    return subprocess.CompletedProcess(
        args=process.args,
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _decode_output(payload: bytes | None) -> str:
    if not payload:
        return ""
    for encoding in ("utf-8", "gbk", "cp936", sys.getdefaultencoding()):
        try:
            return payload.decode(encoding)
        except Exception:
            continue
    return payload.decode(errors="replace")


def _build_details(result: Dict[str, Any], *, scenario_id: str, scenario_title: str, mode: str, url: str | None) -> str:
    payload = {
        "scenario": {
            "scenario_id": scenario_id,
            "scenario_title": scenario_title,
            "mode": mode,
            "url": url,
        },
        "result": {
            "status": result.get("status"),
            "stage": result.get("stage"),
            "requires_human": result.get("requires_human"),
            "dataset_saved": result.get("dataset_saved"),
            "analysis_passed": result.get("analysis_passed"),
            "report_passed": result.get("report_passed"),
            "crawl_strategy": result.get("crawl_strategy"),
            "robots": result.get("robots"),
            "artifacts": result.get("artifacts"),
            "notes": result.get("notes"),
            "error": result.get("error"),
        },
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def record_smoke_memory_capture(
    result: Dict[str, Any],
    *,
    scenario_id: str,
    scenario_title: str,
    mode: str,
    url: str | None = None,
    project_key: str = DEFAULT_PROJECT_KEY,
    tags: Iterable[str] | None = None,
) -> Dict[str, Any]:
    response = {
        "captured": False,
        "capture_path": None,
        "synced": False,
        "sync_path": None,
        "error": None,
    }

    script_path = locate_memory_script()
    if script_path is None:
        response["error"] = "Little C memory script not found"
        return response

    title = f"Smoke Center | {scenario_id} | {result.get('status')}"
    summary = f"{scenario_title} -> {result.get('status')} @ {result.get('stage')}"
    details = _build_details(
        result,
        scenario_id=scenario_id,
        scenario_title=scenario_title,
        mode=mode,
        url=url,
    )
    capture_tags = _normalize_tags(["smoke-center", scenario_id, result.get("status"), result.get("stage"), mode, *(tags or [])])

    try:
        arguments = [
            "capture",
            "--scope",
            "project",
            "--project-key",
            project_key,
            "--title",
            title,
            "--summary",
            summary,
            "--details",
            details,
            "--kind",
            "smoke-run",
        ]
        if capture_tags:
            arguments.extend(["--tags", *capture_tags])

        capture_process = _run(script_path, arguments)
        capture_stdout = capture_process.stdout.strip()
        capture_path = capture_stdout.splitlines()[-1].strip() if capture_stdout else None
        response["captured"] = bool(capture_path)
        response["capture_path"] = capture_path

        sync_process = _run(script_path, ["sync"])
        sync_stdout = sync_process.stdout.strip()
        sync_path = sync_stdout.splitlines()[-1].strip() if sync_stdout else None
        response["synced"] = bool(sync_path)
        response["sync_path"] = sync_path
        return response
    except Exception as exc:  # pragma: no cover
        response["error"] = str(exc)
        return response
