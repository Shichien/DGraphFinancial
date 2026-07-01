$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$zipPath = Join-Path $repoRoot "output\share\DGCheater-demo-data-runtime.zip"
$stagePath = Join-Path $repoRoot ("tmp\demo-data-runtime-" + (Get-Date -Format "yyyyMMddHHmmss"))

$requiredFiles = @(
    "data\amlsim\sample\outputs\accounts.csv",
    "data\amlsim\sample\outputs\tx.csv",
    "data\amlsim\sample\outputs\alerts.csv",
    "data\amlsim\sample\outputs\cash_tx.csv",
    "output\realtime\dgraph_account_prior_12000.joblib",
    "output\realtime\models\xgboost.joblib",
    "output\realtime\models\lightgbm_aux.joblib",
    "output\realtime\models\metadata.json",
    "docs\datasets\data-sharing.md"
)

New-Item -ItemType Directory -Force -Path $stagePath | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $zipPath -Parent) | Out-Null

foreach ($relativePath in $requiredFiles) {
    $sourcePath = Join-Path $repoRoot $relativePath
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "缺少打包文件：$relativePath"
    }

    $targetPath = Join-Path $stagePath $relativePath
    New-Item -ItemType Directory -Force -Path (Split-Path $targetPath -Parent) | Out-Null
    Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
}

Compress-Archive -Path (Join-Path $stagePath "*") -DestinationPath $zipPath -Force

$artifact = Get-Item -LiteralPath $zipPath
Write-Host ("Demo data package created: {0}" -f $artifact.FullName)
Write-Host ("Size: {0:N0} bytes" -f $artifact.Length)
