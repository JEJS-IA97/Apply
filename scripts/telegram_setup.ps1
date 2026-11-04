# RF-14 (spec 004): instala telethon, inicia sesión en Telegram (una vez) y sube los secrets.
# Uso (PowerShell, dentro de la carpeta apply):  .\scripts\telegram_setup.ps1
$ErrorActionPreference = "Stop"
$wheels = Join-Path $PSScriptRoot "..\..\_wheels"
if (Test-Path $wheels) {
    python -m pip install --no-index --find-links $wheels telethon
} else {
    python -m pip install --timeout 120 --retries 10 telethon
}
python -m scripts.telegram_login
gh secret set -f .env --repo JEJS-IA97/Apply
Write-Host "`nListo. Debe aparecer 'Set Actions secret TELEGRAM_SESSION' arriba."
