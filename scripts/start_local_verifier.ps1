$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $projectRoot '.cache/verifier/runtime/llama-server.exe'
$model = Join-Path $projectRoot '.cache/verifier/Qwen_Qwen3-4B-Instruct-2507-Q3_K_S.gguf'
if (!(Test-Path -LiteralPath $runtime) -or !(Test-Path -LiteralPath $model)) {
    throw 'Run venv/Scripts/python.exe scripts/prepare_local_verifier.py first.'
}
& $runtime --model $model --alias evidencelens-verifier --host 127.0.0.1 --port 8081 --ctx-size 8192 --threads 4 --parallel 1 --no-ui --cors-origins http://127.0.0.1:3000 --no-cors-credentials
exit $LASTEXITCODE
