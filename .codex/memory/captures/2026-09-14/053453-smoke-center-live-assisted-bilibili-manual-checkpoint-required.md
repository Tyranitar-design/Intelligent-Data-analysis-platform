# Capture: Smoke Center | live-assisted-bilibili | manual_checkpoint_required

- timestamp: 2026-09-14T05:34:53.459046+08:00
- scope: project
- project_key: intelligent-data-platform
- kind: smoke-run
- summary: Bilibili 人机协同验收 -> manual_checkpoint_required @ waiting_for_human
- tags: smoke-center, live-assisted-bilibili, manual_checkpoint_required, waiting_for_human, live-assisted, bilibili

## Details

{
  "scenario": {
    "scenario_id": "live-assisted-bilibili",
    "scenario_title": "Bilibili 人机协同验收",
    "mode": "live-assisted",
    "url": "https://www.bilibili.com"
  },
  "result": {
    "status": "manual_checkpoint_required",
    "stage": "waiting_for_human",
    "requires_human": true,
    "dataset_saved": false,
    "analysis_passed": false,
    "report_passed": false,
    "crawl_strategy": "assisted-auth",
    "robots": {
      "checked": false
    },
    "artifacts": {
      "login_url": "https://passport.bilibili.com/login",
      "check_url": "https://www.bilibili.com"
    },
    "notes": [
      "请人工完成登录或验证码，然后再点击继续。",
      "当前第一版采用人机协同，不自动绕过验证码。"
    ],
    "error": null
  }
}
