# SPDX-License-Identifier: Apache-2.0
# Load each XAML file in C:\Users\harena\xb into WinUI 3 Gallery's ScratchPad (open on screen), and
# write each element's UI Automation bounds, width and height in px, to measure.txt. Runs in the
# desktop session (runit.ps1); pastes through the clipboard, since the editor is a RichEditBox.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes, System.Windows.Forms
$A = [Windows.Automation.AutomationElement]
$log = @()
$root = $A::RootElement
$wins = $root.FindAll([Windows.Automation.TreeScope]::Children, (New-Object Windows.Automation.PropertyCondition($A::ClassNameProperty, "WinUIDesktopWin32WindowClass")))
$box = $null; $load = $null; $win = $null
foreach ($w in $wins) {
  $b = $w.FindFirst([Windows.Automation.TreeScope]::Descendants, (New-Object Windows.Automation.PropertyCondition($A::AutomationIdProperty, "textbox")))
  if ($b) { $box = $b; $win = $w; $load = $w.FindFirst([Windows.Automation.TreeScope]::Descendants, (New-Object Windows.Automation.PropertyCondition($A::AutomationIdProperty, "loadButton"))) }
}
if (-not $box) { "no scratchpad" | Out-File C:\Users\harena\measure.txt; exit }
foreach ($f in Get-ChildItem C:\Users\harena\xb\*.xaml | Sort Name) {
$xaml = Get-Content -Raw -Encoding UTF8 $f.FullName
[Windows.Forms.Clipboard]::SetText($xaml)
$win.SetFocus(); $box.SetFocus(); Start-Sleep 1
[Windows.Forms.SendKeys]::SendWait("^a"); Start-Sleep 1
[Windows.Forms.SendKeys]::SendWait("^v"); Start-Sleep 2
$load.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke(); Start-Sleep 3
$status = $win.FindFirst([Windows.Automation.TreeScope]::Descendants, (New-Object Windows.Automation.PropertyCondition($A::AutomationIdProperty, "loadStatus")))
$log += "status: " + $status.Current.Name
$all = $win.FindAll([Windows.Automation.TreeScope]::Descendants, [Windows.Automation.Condition]::TrueCondition)
foreach ($e in $all) {
  $id = $e.Current.AutomationId
  if ($id -match '^[tbc]\|') { $r = $e.Current.BoundingRectangle; $log += "$id`t$($r.Width)`t$($r.Height)" }
}
}
$log | Out-File -Encoding utf8 C:\Users\harena\measure.txt
