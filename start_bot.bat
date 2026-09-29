@echo off
rem Windows launcher for the Telegram printer bot (replaces systemd on Linux).
rem Opens the "ПРИНТЕР Freya" window, which runs the bot and restarts it on crash
rem (see autostart\printer_window.ps1). Safe to run twice: only one window starts.
wscript "%~dp0autostart\run_hidden.vbs" printer_window.ps1
