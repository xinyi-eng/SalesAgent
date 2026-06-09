$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$lnk = $shell.CreateShortcut("$desktop\Chrome Debug.lnk")
$lnk.TargetPath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$lnk.Arguments = "--remote-debugging-port=9222"
$lnk.Save()
Write-Host "Shortcut created on Desktop"