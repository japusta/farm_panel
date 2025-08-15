import pyautogui
import subprocess
import time

# Путь к Steam.exe, замени на свой
STEAM_PATH = r"D:\Steam\Steam.exe"

def run_steam(username, password):
    subprocess.Popen(STEAM_PATH)
    time.sleep(10)  # ждём загрузки Steam

    # Ввод логина
    pyautogui.typewrite(username, interval=0.1)
    pyautogui.press('tab')
    
    # Ввод пароля
    pyautogui.typewrite(password, interval=0.1)
    pyautogui.press('enter')

if __name__ == "__main__":
    username = "логин"
    password = "пароль"
    run_steam(username, password)
