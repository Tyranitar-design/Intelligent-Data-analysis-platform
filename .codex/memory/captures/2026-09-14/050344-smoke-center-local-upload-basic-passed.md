# Capture: Smoke Center | local-upload-basic | passed

- timestamp: 2026-09-14T05:03:44.674739+08:00
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
        "name": "smoke_local_contract",
        "table_name": "dataset_smoke_local_contract_20260914_050344",
        "row_count": 2,
        "column_count": 3
      },
      "analysis": {
        "row_count": 2,
        "column_count": 3
      },
      "report": {
        "title": "EDA Report - smoke_local_contract",
        "filepath": "D:\\智能数据分析平台\\backend\\data\\reports\\eda_dataset_smoke_local_contract_20260914_050344_20260914_050344.json"
      }
    },
    "notes": [
      "Local smoke completed successfully"
    ],
    "error": null
  }
}
