<#
.SYNOPSIS
  WebInsight 一键演示脚本（v5 蓝图 F7 · 验收 5.1-4）

.DESCRIPTION
  启动后端(:8000) + 前端(:5173)，等待就绪后打印 90 秒演示路线并打开 showcase。

.EXAMPLE
  .\scripts\demo.ps1               # 启动并打开浏览器
  .\scripts\demo.ps1 -NoBrowser    # 只启动不打开浏览器
  .\scripts\demo.ps1 -Stop         # 停止本脚本启动的进程
#>
param(
    [switch]$Stop,
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$BackendPython = Join-Path $BackendDir "venv\Scripts\python.exe"
$StateFile = Join-Path $PSScriptRoot ".demo-state.json"

$BackendPort = 8000
$FrontendPort = 5173

function Write-Step([string]$Message) { Write-Host "[demo] $Message" -ForegroundColor Cyan }
function Write-Ok([string]$Message) { Write-Host "[ok]   $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host "[warn] $Message" -ForegroundColor Yellow }

function Test-PortBusy([int]$Port) {
    $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Wait-Http([string]$Url, [int]$TimeoutSec = 90) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -eq 200) { return $true }
        } catch { Start-Sleep -Milliseconds 800 }
    }
    return $false
}

if ($Stop) {
    if (-not (Test-Path $StateFile)) {
        Write-Warn "没有记录中的演示进程（state 文件不存在）"
        exit 0
    }
    $state = Get-Content $StateFile -Raw | ConvertFrom-Json
    foreach ($pidValue in @($state.backendPid, $state.frontendPid)) {
        if ($pidValue) {
            try {
                & taskkill.exe /F /T /PID $pidValue *> $null
                Write-Ok "已停止 PID $pidValue"
            } catch {
                Write-Warn "PID $pidValue 已不存在"
            }
        }
    }
    Remove-Item $StateFile -Force -ErrorAction SilentlyContinue
    Write-Ok "演示环境已清理"
    exit 0
}

# ---- 前置检查 ----
Write-Step "检查前置条件 ..."
if (-not (Test-Path $BackendPython)) { throw "未找到后端 venv：$BackendPython（请先安装依赖）" }
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    throw "未找到前端 node_modules（请先在 frontend/ 执行 npm install）"
}
if (Test-PortBusy $BackendPort) { throw "端口 $BackendPort 已被占用——可能开发服务已在运行（run-dev.cmd status 可查看）" }
if (Test-PortBusy $FrontendPort) { throw "端口 $FrontendPort 已被占用——可能开发服务已在运行" }
Write-Ok "前置条件通过"

# ---- 启动后端 ----
Write-Step "启动后端 http://127.0.0.1:$BackendPort ..."
$backendProc = Start-Process -FilePath $BackendPython `
    -ArgumentList @("-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "$BackendPort") `
    -WorkingDirectory $BackendDir -PassThru -WindowStyle Hidden

# ---- 启动前端 ----
Write-Step "启动前端 http://127.0.0.1:$FrontendPort ..."
$node = (Get-Command node -ErrorAction Stop).Source
$viteJs = Join-Path $FrontendDir "node_modules\vite\bin\vite.js"
$frontendProc = Start-Process -FilePath $node `
    -ArgumentList @($viteJs, "dev", "--port", "$FrontendPort", "--host", "127.0.0.1") `
    -WorkingDirectory $FrontendDir -PassThru -WindowStyle Hidden

@{ backendPid = $backendProc.Id; frontendPid = $frontendProc.Id; startedAt = (Get-Date).ToString("s") } |
    ConvertTo-Json | Set-Content -Path $StateFile -Encoding UTF8

# ---- 等待就绪 ----
Write-Step "等待服务就绪（首次启动可能需要数秒）..."
$backOk = Wait-Http "http://127.0.0.1:$BackendPort/health" 120
$frontOk = Wait-Http "http://127.0.0.1:$FrontendPort/" 90
if ($backOk) { Write-Ok "后端就绪：http://127.0.0.1:$BackendPort/docs" } else { Write-Warn "后端未就绪" }
if ($frontOk) { Write-Ok "前端就绪：http://127.0.0.1:$FrontendPort" } else { Write-Warn "前端未就绪" }

# ---- 90 秒演示路线 ----
Write-Host ""
Write-Host "=== 90 秒演示路线（S1 -> S3）===" -ForegroundColor White
Write-Host ""
Write-Host "S1 * 开场（0-10s）数据星云" -ForegroundColor Cyan
Write-Host "     http://127.0.0.1:$FrontendPort/showcase"
Write-Host "     口播：WebInsight —— 任意站点，从可采判定到洞察报告"
Write-Host ""
Write-Host "S2 * 旗舰全链（30-90s）" -ForegroundColor Cyan
Write-Host "     Discover   http://127.0.0.1:$FrontendPort/discover    输入 URL -> 分析 -> 四维判定"
Write-Host "     Collect    http://127.0.0.1:$FrontendPort/collect     创建采集 -> 管道流动 -> 物化数据集"
Write-Host "     Datasets   http://127.0.0.1:$FrontendPort/datasets/2  检索 / 版本历史 / 对比"
Write-Host ""
Write-Host "S3 * 深度彩蛋" -ForegroundColor Cyan
Write-Host "     Compliance http://127.0.0.1:$FrontendPort/compliance  A x B 矩阵 -> 点红点展开四维取证"
Write-Host ""
Write-Host "停止：.\scripts\demo.ps1 -Stop" -ForegroundColor Yellow

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:$FrontendPort/showcase" | Out-Null
    Write-Ok "已打开浏览器（showcase）"
}
