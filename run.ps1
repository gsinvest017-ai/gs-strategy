# gs-strategy one-button launcher (Windows PowerShell).
#
# Usage:
#   .\run.ps1              # = setup + webui
#   .\run.ps1 setup        # create .venv + install deps (idempotent)
#   .\run.ps1 webui        # start webui on http://127.0.0.1:5057
#   .\run.ps1 crawl        # quant-crawl run + fetch-pdfs + rag-ingest
#   .\run.ps1 test         # pytest tests/
#   .\run.ps1 help
#
# Note: For pure-WSL environments, prefer ./run.sh (run from inside WSL).
# This .ps1 targets native Windows Python (PowerShell 5+ / 7+).
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Subcommand = "webui",
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Rest = @()
)

$ErrorActionPreference = "Stop"
$ROOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT_DIR

$VENV_DIR = Join-Path $ROOT_DIR ".venv"
$VENV_PY  = Join-Path $VENV_DIR "Scripts/python.exe"   # Windows venv layout
if (-not (Test-Path $VENV_PY)) {
    # WSL-style layout (when this .ps1 is invoked against a Linux venv)
    $VENV_PY = Join-Path $VENV_DIR "bin/python"
}

$PY_BOOTSTRAP = if ($env:PYTHON) { $env:PYTHON } else { "python" }

function Log($msg) { Write-Host "[run] $msg" }

function Ensure-Venv {
    if (-not (Test-Path $VENV_PY)) {
        Log "creating .venv with $PY_BOOTSTRAP"
        & $PY_BOOTSTRAP -m venv $VENV_DIR
        # refresh path after venv creation (Windows layout)
        $script:VENV_PY = Join-Path $VENV_DIR "Scripts/python.exe"
        if (-not (Test-Path $script:VENV_PY)) {
            $script:VENV_PY = Join-Path $VENV_DIR "bin/python"
        }
    }
}

function Ensure-Deps {
    Ensure-Venv
    Log "installing crawler (editable) + RAG extras"
    & $VENV_PY -m pip install -q --upgrade pip
    & $VENV_PY -m pip install -q -e .
    $reqRag = Join-Path $ROOT_DIR "requirements-rag.txt"
    if (Test-Path $reqRag) {
        & $VENV_PY -m pip install -q -r $reqRag
    }
}

function Ensure-Env {
    $envFile = Join-Path $ROOT_DIR ".env"
    if (-not (Test-Path $envFile)) {
        $envExample = Join-Path $ROOT_DIR ".env.example"
        if (Test-Path $envExample) {
            Log "WARNING: no .env; copying .env.example (fill TEJAPI_KEY for backtest)"
            Copy-Item $envExample $envFile
        } else {
            Log "WARNING: no .env (TEJ-dependent commands will fail)"
        }
    }
}

function Cmd-Setup {
    Ensure-Deps
    Ensure-Env
    Log "setup complete. Next: .\run.ps1 webui"
}

function Cmd-Webui {
    Ensure-Deps
    Log "starting webui on http://127.0.0.1:5057 (Ctrl-C to stop)"
    # Bind to 0.0.0.0 by default so LAN portproxy works (mirrors run_webui.sh)
    & $VENV_PY -m quant_crawler.webui --host ($env:HOST ?? "0.0.0.0") --port ($env:PORT ?? "5057") @Rest
}

function Cmd-Crawl {
    Ensure-Deps
    Ensure-Env
    Log "step 1/3: quant-crawl run --log-run"
    & $VENV_PY -m quant_crawler.cli run --log-run
    Log "step 2/3: quant-crawl fetch-pdfs"
    try { & $VENV_PY -m quant_crawler.cli fetch-pdfs } catch { Log "fetch-pdfs warning (continuing)" }
    Log "step 3/3: quant-crawl rag-ingest"
    try { & $VENV_PY -m quant_crawler.cli rag-ingest } catch { Log "rag-ingest warning (continuing)" }
    Log "crawl pipeline done."
}

function Cmd-Test {
    Ensure-Deps
    & $VENV_PY -m pip install -q pytest
    & $VENV_PY -m pytest tests/ @Rest
}

function Cmd-Help {
    $found = $false
    foreach ($line in Get-Content $MyInvocation.MyCommand.Path) {
        if (-not $found -and $line -match '^# Usage:') { $found = $true }
        if ($found) {
            if ($line -match '^#') { Write-Host ($line -replace '^# ?', '') }
            else { break }
        }
    }
}

switch ($Subcommand) {
    "setup" { Cmd-Setup }
    "webui" { Cmd-Webui }
    "crawl" { Cmd-Crawl }
    "test"  { Cmd-Test }
    { $_ -in "help","-h","--help" } { Cmd-Help }
    default {
        Log "unknown subcommand: $Subcommand"
        Cmd-Help
        exit 2
    }
}
