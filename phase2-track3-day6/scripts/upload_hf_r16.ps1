param(
    [string]$RepoId = "daosonn/lab21-llama32-3b-finance-alpaca-lora-r16",
    [string]$AdapterDir = ".\adapters\r16",
    [string]$StageDir = ".\hf_upload_r16"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command hf -ErrorAction SilentlyContinue)) {
    Write-Host "Hugging Face CLI not found. Install it first:"
    Write-Host 'powershell -ExecutionPolicy ByPass -c "irm https://hf.co/cli/install.ps1 | iex"'
    exit 1
}

$required = @(
    "adapter_config.json",
    "adapter_model.safetensors"
)

foreach ($file in $required) {
    $path = Join-Path $AdapterDir $file
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host "Missing required adapter file: $path"
        Write-Host "Copy/download the Colab folder /content/lab21_llama32_3b_finance_alpaca/r16 into adapters/r16 first."
        exit 1
    }
}

$resolvedStage = Resolve-Path -LiteralPath "." | ForEach-Object { Join-Path $_ $StageDir }
if (Test-Path -LiteralPath $resolvedStage) {
    Remove-Item -LiteralPath $resolvedStage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $resolvedStage | Out-Null

$filesToUpload = @(
    "adapter_config.json",
    "adapter_model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "chat_template.jinja",
    "training_args.bin"
)

foreach ($file in $filesToUpload) {
    $src = Join-Path $AdapterDir $file
    if (Test-Path -LiteralPath $src) {
        Copy-Item -LiteralPath $src -Destination (Join-Path $resolvedStage $file)
    }
}

Copy-Item -LiteralPath ".\HF_MODEL_CARD.md" -Destination (Join-Path $resolvedStage "README.md") -Force

Write-Host "Checking Hugging Face auth..."
$whoami = hf auth whoami 2>&1
Write-Host $whoami
if ($LASTEXITCODE -ne 0 -or ($whoami -join "`n") -match "Not logged in") {
    Write-Host "Hugging Face CLI is not logged in. Run: hf auth login"
    exit 1
}

Write-Host "Uploading $resolvedStage to $RepoId ..."
hf upload $RepoId $resolvedStage --repo-type model
if ($LASTEXITCODE -ne 0) {
    Write-Host "Upload failed."
    exit $LASTEXITCODE
}

Write-Host "Done: https://huggingface.co/$RepoId"
