$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$zipPath = Join-Path $repoRoot "output\share\DGCheater-demo-data-runtime.zip"
$stagePath = Join-Path $repoRoot ("tmp\demo-data-runtime-" + (Get-Date -Format "yyyyMMddHHmmss"))

$requiredFiles = @(
    "data\amlsim\sample\outputs\accounts.csv",
    "data\amlsim\sample\outputs\tx.csv",
    "data\amlsim\sample\outputs\alerts.csv",
    "data\amlsim\sample\outputs\cash_tx.csv",
    "data\runtime-artifacts\output\realtime\dgraph_account_prior_12000.joblib",
    "data\runtime-artifacts\output\realtime\models\xgboost.joblib",
    "data\runtime-artifacts\output\realtime\models\lightgbm_aux.joblib",
    "data\runtime-artifacts\output\realtime\models\metadata.json",
    "data\runtime-artifacts\output\dgraph_fin\models\xgboost.joblib",
    "data\runtime-artifacts\output\dgraph_fin\models\lightgbm_aux.joblib",
    "data\runtime-artifacts\output\dgraph_fin\metrics\xgboost_metrics.json",
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
