# Opens the "ПРИНТЕР Freya" window, which starts the bot and restarts it on crash.
# The window allows only one copy, so running this twice is harmless.
Start-Process wscript.exe -ArgumentList "`"$PSScriptRoot\run_hidden.vbs`" printer_window.ps1"
