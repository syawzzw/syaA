# 验证148条失效路径的实际存在情况
$exists = 0
$notExists = 0
$existsList = @()
$notExistsList = @()

Get-Content "F:\pycode\SyaA\syaA\invalid_paths_list.txt" | ForEach-Object {
    $line = $_.Trim()
    # 匹配包含 Z: 盘路径的行（路径以 .mp4 结尾）
    if ($line -match '(Z:[\\/].+\.mp4)') {
        $path = $Matches[1]
        # 统一转换为反斜杠
        $testPath = $path -replace '/', '\'
        if (Test-Path $testPath) {
            $exists++
            $existsList += $path
        } else {
            $notExists++
            $notExistsList += $path
        }
    }
}

Write-Output "========== 验证结果 =========="
Write-Output "文件存在: $exists"
Write-Output "文件不存在: $notExists"
Write-Output "总计检查: $($exists + $notExists)"
Write-Output ""

if ($notExistsList.Count -gt 0) {
    Write-Output "========== 文件不存在的路径 ($($notExistsList.Count)条) =========="
    $notExistsList | ForEach-Object { Write-Output "  X $_" }
}

Write-Output ""

if ($existsList.Count -gt 0) {
    Write-Output "========== 文件存在的路径 ($($existsList.Count)条) =========="
    $existsList | ForEach-Object { Write-Output "  OK $_" }
}
