Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\jaru\drc-aten"
WshShell.Run "cmd /c start.bat", 1, False
WScript.Quit
