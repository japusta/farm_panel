import subprocess
import time
import pyautogui
import json
import os

CONFIG_PATH = "accounts.json"

def load_accounts():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding='utf-8') as f:
            return json.load(f)
    return []

def save_accounts(accounts):
    with open(CONFIG_PATH, "w", encoding='utf-8') as f:
        json.dump(accounts, f, indent=4, ensure_ascii=False)

def add_account(accounts):
    proxifier_profile = input("Путь до профиля Proxifier (*.ppx): ").strip()
    steam_path = input("Путь до Steam.exe: ").strip()
    username = input("Логин Steam: ").strip()
    password = input("Пароль Steam: ").strip()

    new_account = {
        "proxifier_profile": proxifier_profile,
        "steam_path": steam_path,
        "username": username,
        "password": password
    }

    accounts.append(new_account)
    save_accounts(accounts)
    print("✅ Аккаунт добавлен!")

def select_account(accounts):
    print("🟢 Выбери аккаунт для запуска:")
    for idx, acc in enumerate(accounts):
        print(f"[{idx}] {acc['username']} ({acc['proxifier_profile']})")

    choice = int(input("Введите номер аккаунта: "))
    return accounts[choice]

def run_steam(account):
    subprocess.Popen(['Proxifier.exe', account['proxifier_profile']])
    time.sleep(3)

    subprocess.Popen(account['steam_path'])
    time.sleep(10)

    pyautogui.typewrite(account['username'], interval=0.1)
    pyautogui.press('tab')
    pyautogui.typewrite(account['password'], interval=0.1)
    pyautogui.press('enter')

def main():
    accounts = load_accounts()

    print("Выберите действие:")
    print("[1] Запустить существующий аккаунт")
    print("[2] Добавить новый аккаунт")

    action = input("Ваш выбор (1/2): ").strip()

    if action == "1":
        if not accounts:
            print("❌ Нет сохраненных аккаунтов. Сначала добавьте аккаунт.")
            return
        account = select_account(accounts)
        run_steam(account)

    elif action == "2":
        add_account(accounts)
    else:
        print("Неверный ввод.")

if __name__ == "__main__":
    main()
