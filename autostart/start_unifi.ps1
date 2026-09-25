# Starts UniFi Network Application exactly once (same command as the desktop shortcut).
# If UniFi is already running, does nothing: several copies break its database.
$UniFi = Join-Path $env:USERPROFILE 'Ubiquiti UniFi'

$running = Get-CimInstance Win32_Process -Filter "Name='java.exe' OR Name='javaw.exe'" |
    Where-Object { $_.CommandLine -like '*ace.jar*' }
if ($running) { exit 0 }

$javaArgs = @(
    '--add-opens', 'java.base/java.lang=ALL-UNNAMED',
    '--add-opens', 'java.base/java.time=ALL-UNNAMED',
    '--add-opens', 'java.base/sun.security.util=ALL-UNNAMED',
    '--add-opens', 'java.base/java.io=ALL-UNNAMED',
    '--add-opens', 'java.rmi/sun.rmi.transport=ALL-UNNAMED',
    '-jar', "`"$UniFi\lib\ace.jar`"", 'ui'
)
Start-Process -FilePath "$UniFi\jre\bin\javaw.exe" -ArgumentList $javaArgs -WorkingDirectory $UniFi
