# =========================================================
# ChoiceGuide 定时爬取与部署脚本（方案 A：本地电脑 + Direct Upload）
# 流程：增量爬取 -> 下载配图 -> 构建站点 -> 推送到 GitHub -> 部署到 Cloudflare Pages
# 用法：powershell -NoProfile -ExecutionPolicy Bypass -File c:\web01\run_crawl.ps1
# 日志：c:\web01-data\crawl.log
# =========================================================
$ErrorActionPreference = "Stop"

# --- 配置 ---
$SiteDir   = "c:\web01"
$DataDir   = "c:\web01-data"
$Log       = "$DataDir\crawl.log"
$TokenFile = "$DataDir\.cloudflare-api-token"   # 不进入 git，安全存放 API Token

# --- 加载 Cloudflare API Token（优先环境变量，其次本地文件）---
$Env:CLOUDFLARE_API_TOKEN = if ($env:CLOUDFLARE_API_TOKEN) {
    $env:CLOUDFLARE_API_TOKEN
} elseif (Test-Path $TokenFile) {
    (Get-Content $TokenFile -Raw).Trim()
} else {
    ""
}

function Write-Log($msg, [switch]$IsError) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    if ($IsError) { Write-Host $line -ForegroundColor Red }
    else          { Write-Host $line }
    # 以 UTF-8 追加写入日志，避免中文乱码
    [System.IO.File]::AppendAllText($Log, $line + "`n", [System.Text.Encoding]::UTF8)
}

# 执行外部命令并返回 (exitCode, outputLines)
function Invoke-External($cmd, $argsArray) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $cmd
    $psi.Arguments = $argsArray
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    $p = [System.Diagnostics.Process]::Start($psi)
    $out = $p.StandardOutput.ReadToEnd()
    $err = $p.StandardError.ReadToEnd()
    $p.WaitForExit()
    $lines = @()
    if ($out) { $lines += $out.TrimEnd().Split("`n") }
    if ($err) { $lines += $err.TrimEnd().Split("`n") }
    return $p.ExitCode, $lines
}

# --- 确保目录存在 ---
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null

$Start = Get-Date
Write-Log "===== 开始定时爬取与部署 ====="

Set-Location $SiteDir

try {
    # 1. 增量爬取
    Write-Log "[1/5] 增量爬取 ActiveBeat"
    python scrape_activebeat.py
    if ($LASTEXITCODE -ne 0) { throw "增量爬取失败 (exit=$LASTEXITCODE)" }

    # 2. 下载配图
    Write-Log "[2/5] 下载配图"
    python fetch_images.py
    if ($LASTEXITCODE -ne 0) { throw "配图下载失败 (exit=$LASTEXITCODE)" }

    # 3. 构建站点
    Write-Log "[3/5] 构建站点"
    python build_site_data.py
    if ($LASTEXITCODE -ne 0) { throw "构建失败 (exit=$LASTEXITCODE)" }

    # 4. 推送到 GitHub（仅做代码备份，不触发 Pages）
    Write-Log "[4/5] 推送到 GitHub"
    $changed = git status --porcelain
    if ($changed) {
        git add -A
        $commitMsg = "auto: 定时爬取更新 $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        $ec, $lines = Invoke-External "git" "commit -m `"$commitMsg`""
        $lines | ForEach-Object { Write-Log "  git: $_" }
        if ($ec -ne 0) { throw "git commit 失败 (exit=$ec)" }

        $ec, $lines = Invoke-External "git" "push origin master"
        $lines | ForEach-Object { Write-Log "  git: $_" }
        if ($ec -ne 0) { throw "git push 失败 (exit=$ec)" }
        Write-Log "已推送 $(($changed -split "`n").Count) 个文件变更"
    } else {
        Write-Log "无内容变更，跳过提交推送"
    }

    # 5. 部署到 Cloudflare Pages
    Write-Log "[5/5] 部署到 Cloudflare Pages"
    if (-not $Env:CLOUDFLARE_API_TOKEN) {
        Write-Log "未找到 CLOUDFLARE_API_TOKEN，尝试使用当前 wrangler OAuth 登录状态" -IsError
    }
    $hash = git rev-parse HEAD
    $msg  = git log -1 --pretty=%B
    $ec, $lines = Invoke-External "wrangler" "pages deploy . --project-name choiceguide --branch master --commit-hash `"$hash`" --commit-message `"$msg`""
    $lines | ForEach-Object { Write-Log "  wrangler: $_" }
    if ($ec -ne 0) { throw "wrangler pages deploy 失败 (exit=$ec)" }

    $Dur = [math]::Round(((Get-Date) - $Start).TotalSeconds, 1)
    Write-Log "===== 完成，耗时 ${Dur}s ====="
}
catch {
    Write-Log "!!!!! 失败: $($_.Exception.Message)" -IsError
    exit 1
}
