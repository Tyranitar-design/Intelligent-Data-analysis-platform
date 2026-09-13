# Capture: Smoke Center | local-upload-basic | failed

- timestamp: 2026-09-14T04:55:01.227186+08:00
- scope: project
- project_key: intelligent-data-platform
- kind: smoke-run
- summary: 本地数据主链验收 -> failed @ dataset_save
- tags: smoke-center, local-upload-basic, failed, dataset_save, local

## Details

{
  "scenario": {
    "scenario_id": "local-upload-basic",
    "scenario_title": "本地数据主链验收",
    "mode": "local",
    "url": null
  },
  "result": {
    "status": "failed",
    "stage": "dataset_save",
    "requires_human": false,
    "dataset_saved": false,
    "analysis_passed": false,
    "report_passed": false,
    "crawl_strategy": "local",
    "robots": {
      "checked": false
    },
    "artifacts": {},
    "notes": [],
    "error": "table datasets has no column named dataset_type"
  }
}
