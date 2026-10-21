$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Backend virtual environment not found. Create backend\.venv and install backend\requirements.txt first.'
}

$listeners = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -gt 0) {
    $listenerIds = ($listeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ', '
    throw "Port 8000 already has a server running (PID $listenerIds). Stop that Django server with Ctrl+C, then run this script again."
}

$env:DJANGO_EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
$env:EMAIL_HOST = 'smtp.gmail.com'
$env:EMAIL_PORT = '587'
$env:EMAIL_USE_TLS = 'true'
$env:EMAIL_HOST_USER = 'esicomsuppliers@gmail.com'
$env:DEFAULT_FROM_EMAIL = 'esicomsuppliers@gmail.com'

$securePassword = Read-Host 'Enter a newly created Gmail App Password' -AsSecureString
$env:EMAIL_HOST_PASSWORD = ([System.Net.NetworkCredential]::new('', $securePassword).Password -replace '\s', '')
if (-not $env:EMAIL_HOST_PASSWORD) {
    throw 'No App Password was entered.'
}

Write-Host 'Checking Gmail SMTP login...'
& $python manage.py shell -c "from django.conf import settings; from django.core.mail import get_connection; print('Email backend:', settings.EMAIL_BACKEND); print('SMTP host:', settings.EMAIL_HOST); connection = get_connection(); connection.open(); print('Gmail SMTP login succeeded.'); connection.close()"
if ($LASTEXITCODE -ne 0) {
    throw 'Gmail SMTP login failed. Check that 2-Step Verification is enabled and use a valid, newly created Google App Password.'
}

Write-Host 'Starting the Gmail-configured upload server. Keep this window open.'
& $python manage.py runserver 8000
