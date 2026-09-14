# 本机启动网页，并用 Cloudflare 隧道生成可分享链接（密钥只读本地 .env）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$py = Join-Path $Root ".venv\Scripts\python.exe"
$pip = Join-Path $Root ".venv\Scripts\pip.exe"
if (-not (Test-Path $py)) {
    Write-Host "未找到 .venv，请先按 README 创建虚拟环境。"
    exit 1
}

& $pip install -q waitress
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$old = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
foreach ($procId in $old) {
    if ($procId) { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue }
}

Write-Host "启动本地服务 http://127.0.0.1:5000 ..."
$server = Start-Process -FilePath $py -ArgumentList @(
    "-c", "from waitress import serve; import sys; sys.path.insert(0, r'$Root\MCP_map'); from app import app; serve(app, host='0.0.0.0', port=5000)"
) -WorkingDirectory (Join-Path $Root "MCP_map") -PassThru -WindowStyle Hidden

$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
    Write-Host "正在安装 cloudflared（用于生成公网链接）..."
    winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    $cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
}

if (-not $cloudflared) {
    Write-Host "服务已在本机启动：http://127.0.0.1:5000"
    Write-Host "未找到 cloudflared。安装后重新运行本脚本，或手动执行：cloudflared tunnel --url http://127.0.0.1:5000"
    Write-Host "进程 PID: $($server.Id)  结束服务: Stop-Process -Id $($server.Id)"
    exit 0
}

Write-Host "正在创建公网隧道，请把出现的 https://*.trycloudflare.com 发给别人。"
Write-Host "百度开放平台请把该域名加入浏览器端 Key 的 Referer：https://你的域名/*"
Write-Host "按 Ctrl+C 结束隧道。本地服务 PID: $($server.Id)"
& cloudflared tunnel --url http://127.0.0.1:5000
