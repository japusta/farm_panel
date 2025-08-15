' auto-generated — Steam autologin
Option Explicit
Const DELAY_MS = 9000

Dim USERNAME, PASSWORD
USERNAME = "4dplesenb"
PASSWORD = "Turuzmo3549!"

' --- буфер обмена (через HTMLFile; fallback — MSForms, если есть) ---
Function PutClipboard(s)
  On Error Resume Next
  Dim ok: ok = False
  ' через HTMLFile (обычно работает даже без Office)
  Dim html: Set html = CreateObject("htmlfile")
  If Err.Number = 0 Then
    html.ParentWindow.ClipboardData.SetData "text", s
    If Err.Number = 0 Then ok = True
  End If
  If Not ok Then
    Err.Clear
    ' через MSForms.DataObject (если установлен Office/Forms)
    Dim o: Set o = Nothing
    On Error Resume Next
    Set o = CreateObject("Forms.DataObject")
    If Err.Number = 0 Then
      o.SetText s
      o.PutInClipboard
      If Err.Number = 0 Then ok = True
    End If
  End If
  PutClipboard = ok
End Function

Function EscKeys(s)
  Dim i, ch, t: t = ""
  For i = 1 To Len(s)
    ch = Mid(s, i, 1)
    Select Case ch
      Case "+","^","%","~","(",")","{","}"
        t = t & "{" & ch & "}"
      Case Else
        t = t & ch
    End Select
  Next
  EscKeys = t
End Function

Dim sh: Set sh = CreateObject("WScript.Shell")

' ждём рендер окна
WScript.Sleep DELAY_MS

' несколько попыток активировать окно Steam
Dim i, ok: ok = False
For i = 1 To 40
  If sh.AppActivate("Steam") Then
    ok = True
    Exit For
  End If
  WScript.Sleep 300
Next

If Not ok Then WScript.Quit 0
WScript.Sleep 200

' на всякий — переключим раскладку 2 раза (Alt+Shift), чтобы была EN
sh.SendKeys "%+"
WScript.Sleep 60
sh.SendKeys "%+"
WScript.Sleep 60

' три Shift+Tab — приходим в поле логина
sh.SendKeys "+{TAB}+{TAB}+{TAB}"
WScript.Sleep 80

' ЛОГИН
If PutClipboard(USERNAME) Then
  sh.SendKeys "^a"
  WScript.Sleep 40
  sh.SendKeys "^v"
Else
  sh.SendKeys "^a"
  WScript.Sleep 40
  sh.SendKeys EscKeys("4dplesenb")
End If
WScript.Sleep 120

' ПАРОЛЬ
sh.SendKeys "{TAB}"
WScript.Sleep 80
If PutClipboard(PASSWORD) Then
  sh.SendKeys "^a"
  WScript.Sleep 40
  sh.SendKeys "^v"
Else
  sh.SendKeys "^a"
  WScript.Sleep 40
  sh.SendKeys EscKeys("Turuzmo3549!")
End If
WScript.Sleep 120

' Войти
sh.SendKeys "{ENTER}"
