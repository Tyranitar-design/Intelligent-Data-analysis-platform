# Capture: Smoke Center | local-upload-basic | passed

- timestamp: 2026-05-15T02:10:46.593061+08:00
- scope: project
- project_key: intelligent-data-platform
- kind: smoke-run
- summary: 本地数据主链验收 -> passed @ completed
- tags: smoke-center, local-upload-basic, passed, completed, local

## Details

{
  "scenario": {
    "scenario_id": "local-upload-basic",
    "scenario_title": "本地数据主链验收",
    "mode": "local",
    "url": null
  },
  "result": {
    "status": "passed",
    "stage": "completed",
    "requires_human": false,
    "dataset_saved": true,
    "analysis_passed": true,
    "report_passed": true,
    "crawl_strategy": "local",
    "robots": {
      "checked": false,
      "allowed": true,
      "source": "local"
    },
    "artifacts": {
      "dataset": {
        "name": "smoke_memory_autocapture_verify",
        "table_name": "dataset_smoke_memory_autocapture_verify_20260515_021046",
        "row_count": 2,
        "column_count": 3
      },
      "analysis": {
        "row_count": 2,
        "column_count": 3
      },
      "report": {
        "title": "EDA Report - smoke_memory_autocapture_verify",
        "filepath": "D:\\智能数据分析平台\\backend\\data\\reports\\eda_dataset_smoke_memory_autocapture_verify_20260515_021046_20260515_021046.json"
      }
    },
    "notes": [
      "Local smoke completed successfully"
    ],
    "error": null
  }
}
