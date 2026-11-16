# SPDX-License-Identifier: Apache-2.0
# Run a script in the signed-in desktop session, where UI Automation sees the app, and wait for it.
param([string]$Script)
$name = "uia-" + [guid]::NewGuid().ToString("N").Substring(0,8)
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $Script"
$principal = New-ScheduledTaskPrincipal -UserId "harena" -LogonType Interactive
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal | Out-Null
Start-ScheduledTask -TaskName $name
do { Start-Sleep 2 } while ((Get-ScheduledTask -TaskName $name).State -eq "Running")
Unregister-ScheduledTask -TaskName $name -Confirm:$false
