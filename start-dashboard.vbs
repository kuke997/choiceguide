' ChoiceGuide 管理后台开机自启动（隐藏窗口）
' 位置: %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "python c:\web01-dashboard\server.py 8001", 0, False
