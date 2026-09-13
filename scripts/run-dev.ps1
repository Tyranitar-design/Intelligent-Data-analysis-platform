param(
    [ValidateSet("start", "stop", "status", "check")]
    [string]$Action = "start"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$BackendPython = Join-Path $BackendDir "venv\Scripts\python.exe"
$BackendEnv = Join-Path $BackendDir ".env"
$BackendEnvExample = Join-Path $BackendDir ".env.example"
$FrontendNodeModules = Join-Path $FrontendDir "node_modules"

$BackendWindowTitle = "IDP Backend Dev"
$FrontendWindowTitle = "IDP Frontend Dev"
$BackendPort = 8000
$FrontendPort = 5173

function Write-Section([string]$Message) {
    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Get-DevWindowProcess([string]$WindowTitle) {
    $processes = @(Get-Process | Where-Object { $_.MainWindowTitle -eq $WindowTitle })
    return $processes
}

function Get-PortUsage([int]$Port) {
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
}

function Ensure-BackendEnv {
    if (-not (Test-Path $BackendEnv)) {
        if (-not (Test-Path $BackendEnvExample)) {
            throw "找不到 backend\.env.example，无法创建本地环境文件。"
        }
        Copy-Item -LiteralPath $BackendEnvExample -Destination $BackendEnv
        Write-Host "[OK] 已从 backend/.env.example 创建 backend/.env" -ForegroundColor Green
    }
}

function Test-Prerequisites {
    Write-Section "检查本地开发环境"

    $ok = $true

    if (Test-Path $BackendPython) {
        Write-Host "[OK] 后端虚拟环境已就绪: $BackendPython" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] 缺少后端虚拟环境，请先在 backend 目录创建 venv 并安装 requirements-v2.txt" -ForegroundColor Red
        $ok = $false
    }

    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Host "[OK] npm 命令可用" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] 当前环境找不到 npm，请先安装 Node.js 20+" -ForegroundColor Red
        $ok = $false
    }

    if (Test-Path $FrontendNodeModules) {
        Write-Host "[OK] 前端依赖目录已存在: frontend/node_modules" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] 缺少前端依赖，请先在 frontend 目录执行 npm install" -ForegroundColor Red
        $ok = $false
    }

    Ensure-BackendEnv

    if (-not (Get-PortUsage $BackendPort)) {
        Write-Host "[OK] 后端端口 $BackendPort 可用" -ForegroundColor Green
    } else {
        Write-Host "[WARN] 端口 $BackendPort 已被占用" -ForegroundColor Yellow
    }

    if (-not (Get-PortUsage $FrontendPort)) {
        Write-Host "[OK] 前端端口 $FrontendPort 可用" -ForegroundColor Green
    } else {
        Write-Host "[WARN] 端口 $FrontendPort 已被占用" -ForegroundColor Yellow
    }

    return $ok
}

function Start-Backend {
    $existing = Get-DevWindowProcess $BackendWindowTitle
    if (@($existing).Count -gt 0) {
        Write-Host "[SKIP] 后端开发窗口已存在" -ForegroundColor Yellow
        return
    }

    if (Get-PortUsage $BackendPort) {
        Write-Host "[FAIL] 无法启动后端，端口 $BackendPort 已被占用" -ForegroundColor Red
        return
    }

    $command = "`$Host.UI.RawUI.WindowTitle = '$BackendWindowTitle'; Set-Location -LiteralPath '$BackendDir'; & '.\venv\Scripts\python.exe' -m uvicorn api.main:app --host 0.0.0.0 --port $BackendPort --reload"
    Start-Process -FilePath "pwsh.exe" -WorkingDirectory $BackendDir -ArgumentList @("-NoLogo", "-NoExit", "-Command", $command)
    Write-Host "[OK] 已启动后端开发窗口" -ForegroundColor Green
}

function Start-Frontend {
    $existing = Get-DevWindowProcess $FrontendWindowTitle
    if (@($existing).Count -gt 0) {
        Write-Host "[SKIP] 前端开发窗口已存在" -ForegroundColor Yellow
        return
    }

    if (Get-PortUsage $FrontendPort) {
        Write-Host "[FAIL] 无法启动前端，端口 $FrontendPort 已被占用" -ForegroundColor Red
        return
    }

    $command = "`$Host.UI.RawUI.WindowTitle = '$FrontendWindowTitle'; Set-Location -LiteralPath '$FrontendDir'; npm run dev -- --host 0.0.0.0 --port $FrontendPort"
    Start-Process -FilePath "pwsh.exe" -WorkingDirectory $FrontendDir -ArgumentList @("-NoLogo", "-NoExit", "-Command", $command)
    Write-Host "[OK] 已启动前端开发窗口" -ForegroundColor Green
}

function Stop-DevWindows {
    Write-Section "停止开发窗口"

    $stopped = $false
    foreach ($title in @($BackendWindowTitle, $FrontendWindowTitle)) {
        $processes = Get-DevWindowProcess $title
        if (@($processes).Count -gt 0) {
            $processes | Stop-Process -Force
            Write-Host "[OK] 已关闭 $title" -ForegroundColor Green
            $stopped = $true
        }
    }

    if (-not $stopped) {
        Write-Host "[INFO] 当前没有由 run-dev 管理的开发窗口" -ForegroundColor Yellow
    }
}

function Show-Status {
    Write-Section "本地开发状态"

    $backendWindow = Get-DevWindowProcess $BackendWindowTitle
    $frontendWindow = Get-DevWindowProcess $FrontendWindowTitle
    $backendPortUsage = Get-PortUsage $BackendPort
    $frontendPortUsage = Get-PortUsage $FrontendPort

    Write-Host ("后端窗口: " + ($(if (@($backendWindow).Count -gt 0) { "运行中" } else { "未运行" })))
    Write-Host ("前端窗口: " + ($(if (@($frontendWindow).Count -gt 0) { "运行中" } else { "未运行" })))
    Write-Host ("后端端口 ${BackendPort}: " + ($(if ($backendPortUsage) { "占用中" } else { "空闲" })))
    Write-Host ("前端端口 ${FrontendPort}: " + ($(if ($frontendPortUsage) { "占用中" } else { "空闲" })))
    Write-Host ""
    Write-Host "后端地址: http://127.0.0.1:$BackendPort"
    Write-Host "前端地址: http://127.0.0.1:$FrontendPort"
}

switch ($Action) {
    "check" {
        if (-not (Test-Prerequisites)) {
            exit 1
        }
        Show-Status
    }
    "status" {
        Show-Status
    }
    "start" {
        if (-not (Test-Prerequisites)) {
            exit 1
        }
        Write-Section "启动本地开发环境"
        Start-Backend
        Start-Frontend
        Start-Sleep -Seconds 2
        Show-Status
    }
    "stop" {
        Stop-DevWindows
        Show-Status
    }
}
