# Capture: Smoke Center | live-assisted-bilibili | failed

- timestamp: 2026-09-14T04:53:27.733507+08:00
- scope: project
- project_key: intelligent-data-platform
- kind: smoke-run
- summary: Bilibili assisted auth -> failed @ session_reuse_check
- tags: smoke-center, live-assisted-bilibili, failed, session_reuse_check, live-assisted, bilibili

## Details

{
  "scenario": {
    "scenario_id": "live-assisted-bilibili",
    "scenario_title": "Bilibili assisted auth",
    "mode": "live-assisted",
    "url": "https://www.bilibili.com"
  },
  "result": {
    "status": "failed",
    "stage": "session_reuse_check",
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
      "check_url": "https://www.bilibili.com",
      "auth_status": {
        "is_logged_in": false,
        "message": "无 Cookie"
      }
    },
    "notes": [
      "未检测到有效登录态，请重新开始并完成人工登录。"
    ],
    "error": "无 Cookie"
  }
}
