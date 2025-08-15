import os
import sys
import json
import time
import threading
import subprocess
import pyautogui
import requests
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, 
                             QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QTextEdit,
                             QLabel, QComboBox, QLineEdit, QFileDialog)
from PyQt5.QtCore import Qt, QTimer

CONFIG_PATH = "accounts.json"
SANDBOX_PATH = "C:\\Program Files\\Avast Software\\Avast\\sbox.exe"
STEAM_API_KEY = "YOUR_STEAM_API_KEY"  # Замените на реальный ключ

class BotManager:
    def __init__(self):
        self.accounts = []
        self.processes = {}
        self.load_accounts()
        
    def load_accounts(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding='utf-8') as f:
                self.accounts = json.load(f)
        return self.accounts
    
    def save_accounts(self):
        with open(CONFIG_PATH, "w", encoding='utf-8') as f:
            json.dump(self.accounts, f, indent=4, ensure_ascii=False)
    
    def add_account(self, account_data):
        account_data["status"] = "Stopped"
        account_data["last_run"] = ""
        account_data["total_time"] = 0
        account_data["cases_dropped"] = 0
        account_data["xp_earned"] = 0
        self.accounts.append(account_data)
        self.save_accounts()
    
    def remove_account(self, index):
        if 0 <= index < len(self.accounts):
            if self.accounts[index]["username"] in self.processes:
                self.stop_account(index)
            del self.accounts[index]
            self.save_accounts()
    
    def start_account(self, index):
        if 0 <= index < len(self.accounts):
            account = self.accounts[index]
            
            # Создаем командный файл для запуска в песочнице
            bat_content = f'''
@echo off
start "" "{account['proxifier_path']}" /NoSplash
timeout /t 3
"{account['steam_path']}" -login {account['username']} {account['password']} -applaunch 730 -novid -console -windowed -w 1280 -h 720
'''
            bat_path = f"launch_{account['username']}.bat"
            with open(bat_path, "w") as f:
                f.write(bat_content)
            
            # Запускаем в песочнице Avast
            cmd = f'"{SANDBOX_PATH}" /run /silent {os.path.abspath(bat_path)}'
            process = subprocess.Popen(cmd, shell=True)
            
            self.processes[account["username"]] = process
            self.accounts[index]["status"] = "Running"
            self.accounts[index]["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # Запускаем мониторинг игры
            threading.Thread(
                target=self.monitor_game, 
                args=(index,),
                daemon=True
            ).start()
    
    def stop_account(self, index):
        if 0 <= index < len(self.accounts):
            username = self.accounts[index]["username"]
            if username in self.processes:
                self.processes[username].terminate()
                del self.processes[username]
            self.accounts[index]["status"] = "Stopped"
    
    def monitor_game(self, index):
        """Мониторинг состояния игры и выполнение действий бота"""
        account = self.accounts[index]
        start_time = time.time()
        
        try:
            # Ожидаем запуска игры (упрощенная версия)
            time.sleep(120)
            
            # Основной игровой цикл
            while self.accounts[index]["status"] == "Running":
                # Здесь будет логика бота
                self.perform_bot_actions(index)
                
                # Обновляем статистику
                play_time = int(time.time() - start_time)
                self.accounts[index]["total_time"] += play_time
                
                # Обновляем каждые 5 минут
                time.sleep(300)
                
        except Exception as e:
            print(f"Ошибка в аккаунте {account['username']}: {str(e)}")
        
        self.accounts[index]["status"] = "Stopped"
    
    def perform_bot_actions(self, index):
        """Основные действия бота в игре"""
        # Случайные движения и действия
        actions = [
            {'key': 'w', 'duration': random.uniform(1.0, 3.0)},
            {'key': 'a', 'duration': random.uniform(0.5, 1.5)},
            {'mouse': 'left', 'duration': random.uniform(0.1, 0.3)},
            {'key': 's', 'duration': random.uniform(0.5, 1.0)},
            {'key': 'space', 'duration': 0.1},
        ]
        
        # Выполняем 5-10 случайных действий
        for _ in range(random.randint(5, 10)):
            action = random.choice(actions)
            if 'key' in action:
                pyautogui.keyDown(action['key'])
                time.sleep(action['duration'])
                pyautogui.keyUp(action['key'])
            elif 'mouse' in action:
                pyautogui.mouseDown(button=action['mouse'])
                time.sleep(action['duration'])
                pyautogui.mouseUp(button=action['mouse'])
            
            time.sleep(random.uniform(0.1, 1.5))
            
            # Случайное движение мыши
            pyautogui.moveRel(
                random.randint(-50, 50),
                random.randint(-50, 50),
                duration=random.uniform(0.2, 0.8)
            )
        
        # Имитация выхода из матча (каждые 30-60 минут)
        if random.random() > 0.8:
            pyautogui.press('esc')
            time.sleep(2)
            pyautogui.click(x=100, y=300)  # Кнопка Disconnect
            time.sleep(10)
            # Перезаход в игру
            pyautogui.click(x=960, y=540)  # Play button
            time.sleep(3)
            pyautogui.click(x=800, y=400)  # Casual mode
            time.sleep(3)
            pyautogui.click(x=960, y=700)  # Confirm
            
            # Фиксируем вероятный дроп кейса
            if random.random() > 0.9:
                self.accounts[index]["cases_dropped"] += 1
                self.accounts[index]["xp_earned"] += random.randint(500, 1500)
    
    def check_vac_status(self, username):
        """Проверка VAC статуса через Steam API"""
        try:
            # Получаем SteamID по логину (упрощенно)
            response = requests.get(
                f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/",
                params={
                    'key': STEAM_API_KEY,
                    'vanityurl': username
                }
            )
            steamid = response.json().get('response', {}).get('steamid', '')
            
            if steamid:
                response = requests.get(
                    f"https://api.steampowered.com/ISteamUser/GetPlayerBans/v1/",
                    params={'key': STEAM_API_KEY, 'steamids': steamid}
                )
                bans = response.json().get('players', [{}])[0]
                return "Banned" if bans.get('VACBanned') else "Clean"
        except:
            return "Error"
        return "Unknown"


class AccountDialog(QWidget):
    """Диалог добавления аккаунта"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить аккаунт")
        self.setGeometry(300, 300, 400, 300)
        
        layout = QVBoxLayout()
        
        self.proxifier_label = QLabel("Путь до Proxifier.exe:")
        self.proxifier_path = QLineEdit()
        self.proxifier_browse = QPushButton("Обзор")
        self.proxifier_browse.clicked.connect(self.browse_proxifier)
        
        self.profile_label = QLabel("Профиль Proxifier (*.ppx):")
        self.profile_path = QLineEdit()
        self.profile_browse = QPushButton("Обзор")
        self.profile_browse.clicked.connect(self.browse_profile)
        
        self.steam_label = QLabel("Путь до Steam.exe:")
        self.steam_path = QLineEdit()
        self.steam_browse = QPushButton("Обзор")
        self.steam_browse.clicked.connect(self.browse_steam)
        
        self.username_label = QLabel("Логин Steam:")
        self.username_input = QLineEdit()
        
        self.password_label = QLabel("Пароль Steam:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.accept)
        
        layout.addWidget(self.proxifier_label)
        layout.addWidget(self.proxifier_path)
        layout.addWidget(self.proxifier_browse)
        layout.addWidget(self.profile_label)
        layout.addWidget(self.profile_path)
        layout.addWidget(self.profile_browse)
        layout.addWidget(self.steam_label)
        layout.addWidget(self.steam_path)
        layout.addWidget(self.steam_browse)
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.save_btn)
        
        self.setLayout(layout)
    
    def browse_proxifier(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите Proxifier.exe", "", "Executable Files (*.exe)"
        )
        if path:
            self.proxifier_path.setText(path)
    
    def browse_profile(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите профиль Proxifier", "", "Proxifier Profiles (*.ppx)"
        )
        if path:
            self.profile_path.setText(path)
    
    def browse_steam(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите Steam.exe", "", "Executable Files (*.exe)"
        )
        if path:
            self.steam_path.setText(path)
    
    def accept(self):
        self.close()
    
    def get_data(self):
        return {
            "proxifier_path": self.proxifier_path.text(),
            "proxifier_profile": self.profile_path.text(),
            "steam_path": self.steam_path.text(),
            "username": self.username_input.text(),
            "password": self.password_input.text()
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bot_manager = BotManager()
        self.initUI()
        self.load_accounts()
    
    def initUI(self):
        self.setWindowTitle("CS2 Bot Farm Manager")
        self.setGeometry(100, 100, 1000, 600)
        
        # Основные виджеты
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Логин", "Статус", "Последний запуск", "Время работы", 
            "Кейсы", "Опыт", "VAC статус", "Действия"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Панель кнопок
        self.add_btn = QPushButton("Добавить аккаунт")
        self.add_btn.clicked.connect(self.add_account)
        
        self.remove_btn = QPushButton("Удалить аккаунт")
        self.remove_btn.clicked.connect(self.remove_account)
        
        self.start_btn = QPushButton("Запустить выбранные")
        self.start_btn.clicked.connect(self.start_accounts)
        
        self.stop_btn = QPushButton("Остановить выбранные")
        self.stop_btn.clicked.connect(self.stop_accounts)
        
        self.refresh_btn = QPushButton("Обновить статусы")
        self.refresh_btn.clicked.connect(self.check_vac_statuses)
        
        # Лог
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        
        # Расположение
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.refresh_btn)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.table)
        main_layout.addWidget(self.log)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        # Таймер для обновления UI
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_table)
        self.timer.start(5000)  # Обновление каждые 5 секунд
    
    def log_message(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.log.append(f"{timestamp} {message}")
    
    def load_accounts(self):
        self.bot_manager.load_accounts()
        self.update_table()
    
    def update_table(self):
        accounts = self.bot_manager.accounts
        self.table.setRowCount(len(accounts))
        
        for i, acc in enumerate(accounts):
            self.table.setItem(i, 0, QTableWidgetItem(acc["username"]))
            self.table.setItem(i, 1, QTableWidgetItem(acc["status"]))
            self.table.setItem(i, 2, QTableWidgetItem(acc.get("last_run", "")))
            self.table.setItem(i, 3, QTableWidgetItem(self.format_time(acc.get("total_time", 0))))
            self.table.setItem(i, 4, QTableWidgetItem(str(acc.get("cases_dropped", 0))))
            self.table.setItem(i, 5, QTableWidgetItem(str(acc.get("xp_earned", 0))))
            
            # VAC статус
            vac_item = QTableWidgetItem(acc.get("vac_status", "Unknown"))
            if vac_item.text() == "Banned":
                vac_item.setBackground(Qt.red)
            elif vac_item.text() == "Clean":
                vac_item.setBackground(Qt.green)
            self.table.setItem(i, 6, vac_item)
            
            # Кнопки действий
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            
            start_btn = QPushButton("Старт")
            start_btn.clicked.connect(lambda _, idx=i: self.start_account(idx))
            action_layout.addWidget(start_btn)
            
            stop_btn = QPushButton("Стоп")
            stop_btn.clicked.connect(lambda _, idx=i: self.stop_account(idx))
            action_layout.addWidget(stop_btn)
            
            action_widget.setLayout(action_layout)
            self.table.setCellWidget(i, 7, action_widget)
    
    def format_time(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}ч {minutes}м"
    
    def add_account(self):
        dialog = AccountDialog(self)
        dialog.exec_()
        account_data = dialog.get_data()
        
        if all(account_data.values()):
            self.bot_manager.add_account(account_data)
            self.update_table()
            self.log_message(f"Добавлен аккаунт: {account_data['username']}")
    
    def remove_account(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            return
        
        for idx in selected:
            row = idx.row()
            if 0 <= row < len(self.bot_manager.accounts):
                username = self.bot_manager.accounts[row]["username"]
                self.bot_manager.remove_account(row)
                self.log_message(f"Удален аккаунт: {username}")
        
        self.update_table()
    
    def start_account(self, index):
        self.bot_manager.start_account(index)
        self.update_table()
        self.log_message(f"Запуск аккаунта: {self.bot_manager.accounts[index]['username']}")
    
    def stop_account(self, index):
        self.bot_manager.stop_account(index)
        self.update_table()
        self.log_message(f"Остановка аккаунта: {self.bot_manager.accounts[index]['username']}")
    
    def start_accounts(self):
        selected = self.table.selectionModel().selectedRows()
        for idx in selected:
            self.start_account(idx.row())
    
    def stop_accounts(self):
        selected = self.table.selectionModel().selectedRows()
        for idx in selected:
            self.stop_account(idx.row())
    
    def check_vac_statuses(self):
        for i, acc in enumerate(self.bot_manager.accounts):
            status = self.bot_manager.check_vac_status(acc["username"])
            self.bot_manager.accounts[i]["vac_status"] = status
        self.update_table()
        self.log_message("Статусы VAC обновлены")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())