# =========================================================
# 保存 Cloudflare API Token 到本地安全位置
# 用法：powershell -NoProfile -ExecutionPolicy Bypass -File c:\web01\save_api_token.ps1
# 提示输入 token（输入时不会显示），保存到 c:\web01-data\.cloudflare-api-token
# =========================================================
$ErrorActionPreference = "Stop"

$DataDir = "c:\web01-data"
$TokenFile = "$DataDir\.cloudflare-api-token"

New-Item -ItemType Directory -Path $DataDir -Force | Out-Null

Write-Host "请粘贴 Cloudflare API Token（输入时不会显示）：" -ForegroundColor Cyan
$token = Read-Host -AsSecureString
$plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($token)).Trim()

if (-not $plain) {
    Write-Error "Token 不能为空"
    exit 1
}

if ($plain.Length -lt 20) {
    Write-Error "Token 太短，请检查是否复制完整"
    exit 1
}

[System.IO.File]::WriteAllText($TokenFile, $plain, [System.Text.Encoding]::UTF8)
Write-Host "已保存到: $TokenFile" -ForegroundColor Green
Write-Host "下一步：运行 c:\web01\run_crawl.ps1 测试部署" -ForegroundColor Green
