# Starts the printer bot exactly once (two copies would fight over Telegram polling).
$App = Split-Path -Parent $PSScriptRoot

$running = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*bot.main*' }
if ($running) { exit 0 }

Start-Process -FilePath "$App\start_bot.bat" -WorkingDirectory $App -WindowStyle Minimized
