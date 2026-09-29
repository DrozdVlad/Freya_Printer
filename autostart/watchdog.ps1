# Сторож: запускається планувальником щохвилини. Якщо вікно принтера не працює
# (вбили процес, зависло й закрилося) — записує це в журнал і запускає вікно знову.
$App = Split-Path -Parent $PSScriptRoot
$Logs = Join-Path $App 'logs'

$m = $null
if ([Threading.Mutex]::TryOpenExisting('Local\FreyaPrinterWindow', [ref]$m)) {
    $m.Dispose()
    exit 0
}

New-Item -ItemType Directory -Force $Logs | Out-Null
Add-Content (Join-Path $Logs 'supervisor.log') -Encoding UTF8 `
    ('{0:yyyy-MM-dd HH:mm:ss}  Сторож: вікно принтера не працювало — запускаю знову' -f (Get-Date))
Start-Process wscript.exe -ArgumentList "`"$PSScriptRoot\run_hidden.vbs`" printer_window.ps1 -FromWatchdog"
