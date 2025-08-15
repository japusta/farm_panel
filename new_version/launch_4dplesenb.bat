@echo off
taskkill /F /IM steam.exe >nul 2>&1
taskkill /F /IM steamwebhelper.exe >nul 2>&1
timeout /t 1 >nul
"D:/Steam/steam.exe" -login 4dplesenb 'Turuzmo3549!' -applaunch 730 -novid -console -windowed -w 1280 -h 720 -noreactlogin -rememberpassword
timeout /t 2 >nul
start "" wscript.exe "C:\Users\capta\Desktop\farm_scripts\new_version\autologin_4dplesenb.vbs"
