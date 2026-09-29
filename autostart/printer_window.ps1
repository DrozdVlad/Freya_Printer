# Вікно «ПРИНТЕР Freya»: тримає бота запущеним, перезапускає його при падінні,
# питає підтвердження перед закриттям і пише журнал подій у logs\supervisor.log.
# Запускати через run_hidden.vbs (без консолі). Одночасно працює лише одна копія.
param([switch]$FromWatchdog)

Add-Type -AssemblyName System.Windows.Forms, System.Drawing

$App = Split-Path -Parent $PSScriptRoot
Set-Location $App
$Logs = Join-Path $App 'logs'
New-Item -ItemType Directory -Force $Logs | Out-Null
$EventLog = Join-Path $Logs 'supervisor.log'
$Who = "$env:USERDOMAIN\$env:USERNAME"
$ExitConfig = 78

$created = $false
$mutex = New-Object System.Threading.Mutex($true, 'Local\FreyaPrinterWindow', [ref]$created)
if (-not $created) { exit 0 }

# OBS може тримати процесор на 100% — вікно й бот не повинні через це зависати.
[Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'AboveNormal'

$script:list = $null
function Write-Event([string]$text) {
    $line = '{0:yyyy-MM-dd HH:mm:ss}  {1}' -f (Get-Date), $text
    Add-Content -Path $EventLog -Value $line -Encoding UTF8
    if ($script:list) {
        $script:list.Items.Insert(0, $line)
        while ($script:list.Items.Count -gt 300) { $script:list.Items.RemoveAt(300) }
    }
}

function Get-BotProcesses {
    Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='cmd.exe'" |
        Where-Object { $_.CommandLine -like '*bot.main*' -or $_.CommandLine -like '*start_bot.bat*' }
}

function Stop-Tree([int]$processId) {
    & taskkill.exe /PID $processId /T /F 2>$null | Out-Null
}

$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$script:bot = $null
$script:restartAt = $null
$script:stopping = $false
$script:needPriority = $false

function Start-Bot {
    Add-Content (Join-Path $Logs 'bot.log') ('[{0:yyyy-MM-dd HH:mm:ss}] starting bot' -f (Get-Date)) -Encoding UTF8
    $script:bot = Start-Process -FilePath $env:ComSpec -WorkingDirectory $App -WindowStyle Hidden -PassThru `
        -ArgumentList '/d /c ".venv\Scripts\python.exe -m bot.main >> logs\bot.log 2>&1"'
    $null = $script:bot.Handle  # без цього ExitCode після завершення буде порожнім
    $script:needPriority = $true
    Write-Event "Бот запущено (PID $($script:bot.Id))"
}

function Stop-Bot {
    if ($script:bot -and -not $script:bot.HasExited) { Stop-Tree $script:bot.Id }
    Get-BotProcesses | ForEach-Object { Stop-Tree $_.ProcessId }
    $script:bot = $null
}

# --- вікно ---
$form = New-Object Windows.Forms.Form
$form.Text = 'ПРИНТЕР Freya (Telegram-бот) — НЕ ЗАКРИВАТИ'
$form.Size = New-Object Drawing.Size(720, 420)
$form.StartPosition = 'CenterScreen'
$form.WindowState = 'Minimized'
$form.Font = New-Object Drawing.Font('Segoe UI', 10)

$status = New-Object Windows.Forms.Label
$status.Dock = 'Top'
$status.Height = 44
$status.TextAlign = 'MiddleCenter'
$status.Font = New-Object Drawing.Font('Segoe UI', 14, [Drawing.FontStyle]::Bold)
$status.ForeColor = 'White'

$buttons = New-Object Windows.Forms.FlowLayoutPanel
$buttons.Dock = 'Bottom'
$buttons.Height = 44
$buttons.Padding = New-Object Windows.Forms.Padding(6)

$btnRestart = New-Object Windows.Forms.Button
$btnRestart.Text = 'Перезапустити бота'
$btnRestart.AutoSize = $true
$btnLog = New-Object Windows.Forms.Button
$btnLog.Text = 'Журнал бота'
$btnLog.AutoSize = $true
$buttons.Controls.AddRange(@($btnRestart, $btnLog))

$script:list = New-Object Windows.Forms.ListBox
$script:list.Dock = 'Fill'
$script:list.Font = New-Object Drawing.Font('Consolas', 9)
$script:list.HorizontalScrollbar = $true

$form.Controls.Add($script:list)
$form.Controls.Add($buttons)
$form.Controls.Add($status)

function Set-Status([string]$text, [string]$color) {
    $status.Text = $text
    $status.BackColor = $color
}

if (Test-Path $EventLog) {
    Get-Content $EventLog -Tail 100 -Encoding UTF8 | ForEach-Object { $script:list.Items.Insert(0, $_) }
}

$btnRestart.Add_Click({
    Write-Event "Перезапуск вручну ($Who)"
    Stop-Bot
    Start-Bot
})
$btnLog.Add_Click({ Start-Process notepad.exe (Join-Path $Logs 'bot.log') })

# Закриття вікна бота НЕ зупиняє: вікно одразу відкривається знову й підхоплює
# бота, що працює. Зупиняє бота лише вимкнення Windows.
$form.Add_FormClosing({
    param($sender, $e)
    switch ($e.CloseReason) {
        'WindowsShutDown' {
            Write-Event 'Вимкнення або перезавантаження Windows — бот зупинено'
            $script:stopping = $true
            Stop-Bot
            return
        }
        'UserClosing' {
            $answer = [Windows.Forms.MessageBox]::Show($form,
                "Закрити вікно принтера?`n`nБот продовжить працювати, вікно відкриється знову.",
                'ПРИНТЕР Freya', 'YesNo', 'Warning', 'Button2')
            if ($answer -ne 'Yes') {
                $e.Cancel = $true
                Write-Event "Спроба закрити вікно — скасовано ($Who)"
                return
            }
            Write-Event "ВІКНО ЗАКРИТО ВРУЧНУ ($Who) — бот працює далі, вікно відкривається знову"
        }
        'TaskManagerClosing' { Write-Event "Вікно закрито через Диспетчер задач ($Who) — бот працює далі, вікно відкривається знову" }
        default { Write-Event "Вікно закрито ($($e.CloseReason)) — бот працює далі, вікно відкривається знову" }
    }
    $script:stopping = $true
    $timer.Stop()
    $mutex.ReleaseMutex()
    Start-Process wscript.exe -ArgumentList "`"$PSScriptRoot\run_hidden.vbs`" printer_window.ps1 -FromWatchdog"
})

$timer = New-Object Windows.Forms.Timer
$timer.Interval = 2000
$timer.Add_Tick({
    if ($script:stopping) { return }

    if ($script:bot -and $script:bot.HasExited) {
        $rc = $script:bot.ExitCode
        $script:bot = $null
        if ($rc -eq $ExitConfig) {
            Write-Event 'Бот зупинився: помилка налаштувань (.env), див. журнал бота. Автоперезапуск не допоможе.'
            Set-Status 'ПОМИЛКА НАЛАШТУВАНЬ — див. журнал' 'Firebrick'
            return
        }
        Write-Event "Бот зупинився (код $rc) — перезапуск через 5 с"
        $script:restartAt = (Get-Date).AddSeconds(5)
    }

    if (-not $script:bot -and $script:restartAt -and (Get-Date) -ge $script:restartAt) {
        $script:restartAt = $null
        Start-Bot
    }

    if ($script:needPriority) {
        $py = Get-BotProcesses | Where-Object Name -eq 'python.exe'
        if ($py) {
            $py | ForEach-Object { try { (Get-Process -Id $_.ProcessId).PriorityClass = 'AboveNormal' } catch {} }
            $script:needPriority = $false
        }
    }

    if ($script:bot) { Set-Status 'ПРАЦЮЄ' 'ForestGreen' } else { Set-Status 'ПЕРЕЗАПУСК…' 'DarkOrange' }
})

# --- старт ---
$how = if ($FromWatchdog) { 'повторно (після закриття / сторожем)' } else { 'автозапуск / вручну' }
Write-Event "Вікно запущено: $how, користувач $Who"

$found = @(Get-BotProcesses)
# Старий запуск через start_bot.bat має власний цикл перезапуску — прибираємо, щоб не було двох ботів.
$legacy = $found | Where-Object { $_.CommandLine -like '*start_bot.bat*' }
if ($legacy) {
    Write-Event 'Знайдено старий запуск через start_bot.bat — замінюю на вікно'
    $legacy | ForEach-Object { Stop-Tree $_.ProcessId }
    Start-Sleep -Seconds 2
    $found = @(Get-BotProcesses)
}
# Бот, що вже працює (після закриття вікна), підхоплюємо без перезапуску.
$ids = $found | ForEach-Object { $_.ProcessId }
$top = $found | Where-Object { $ids -notcontains $_.ParentProcessId } | Select-Object -First 1
if ($top) {
    try {
        $script:bot = Get-Process -Id $top.ProcessId -ErrorAction Stop
        $null = $script:bot.Handle
        Write-Event "Бот уже працює (PID $($top.ProcessId)) — підхоплено без перезапуску"
    } catch { $script:bot = $null }
}
if (-not $script:bot) { Start-Bot }
Set-Status 'ПРАЦЮЄ' 'ForestGreen'
$timer.Start()

[Windows.Forms.Application]::Run($form)
try { $mutex.ReleaseMutex() } catch {}
