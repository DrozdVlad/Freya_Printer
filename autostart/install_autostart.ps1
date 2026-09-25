# Adds the printer bot and UniFi to Windows startup (runs at sign-in),
# and points the desktop UniFi icon at the single-copy launcher.
$app = Split-Path -Parent $PSScriptRoot
$ps = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$startup = [Environment]::GetFolderPath('Startup')
$unifi = Join-Path $env:USERPROFILE 'Ubiquiti UniFi'
$sh = New-Object -ComObject WScript.Shell

function New-Link($path, $script, $icon, $workDir) {
    $l = $sh.CreateShortcut($path)
    $l.TargetPath = $ps
    $l.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
    $l.WorkingDirectory = $workDir
    $l.WindowStyle = 7
    if ($icon) { $l.IconLocation = $icon }
    $l.Save()
}

New-Link "$startup\Freya Printer Bot.lnk" "$app\autostart\start_bot.ps1" $null $app
New-Link "$startup\UniFi.lnk" "$app\autostart\start_unifi.ps1" "$unifi\unifi-network.ico" $unifi

$desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) 'UniFi.lnk'
if (Test-Path $desktop) {
    Copy-Item $desktop "$app\autostart\UniFi.original.lnk" -Force
    New-Link $desktop "$app\autostart\start_unifi.ps1" "$unifi\unifi-network.ico" $unifi
}
Write-Host "Autostart installed in $startup"
