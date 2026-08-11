# =========================================================
# ChoiceGuide 定时爬取脚本（方案 X：本地电脑常开）
# 流程：增量爬取 -> 下载配图 -> 构建站点与看板 -> 推送到 GitHub（触发 Cloudflare Pages 自动部署）
# 用法：powershell -NoProfile -ExecutionPolicy Bypass -File c:\web01\run_crawl.ps1
# 日志：c:\web01-data\crawl.log
# =========================================================
$ErrorActionPreference = "Stop"
$Log = "c:\web01-data\crawl.log"
$Start = Get-Date

function Write-Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $Log -Value $line
}

Write-Log "===== 开始定时爬取 ====="
Set-Location "c:\web01"

try {
    Write-Log "[1/4] 增量爬取"
    python scrape_activebeat.py 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "增量爬取失败(exit=$LASTEXITCODE)" }

    Write-Log "[2/4] 下载配图"
    python fetch_images.py 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "配图下载失败(exit=$LASTEXITCODE)" }

    Write-Log "[3/4] 构建站点与看板"
    python build_site_data.py 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "构建失败(exit=$LASTEXITCODE)" }

    Write-Log "[4/4] 推送 GitHub（触发自动部署）"
    $changed = git status --porcelain
    if ($changed) {
        git add -A
        git commit -m "auto: 定时爬取更新 $(Get-Date -Format 'yyyy-MM-dd HH:mm')" | Out-Null
        git push origin master 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "git push 失败(exit=$LASTEXITCODE)" }
        Write-Log "已推送 $(($changed -split "`n").Count) 个文件变更"
    } else {
        Write-Log "无内容变更，跳过提交推送"
    }

    $Dur = [math]::Round(((Get-Date) - $Start).TotalSeconds, 1)
    Write-Log "===== 完成，耗时 ${Dur}s ====="
}
catch {
    Write-Log "!!!!! 失败: $($_.Exception.Message)"
    exit 1
}
