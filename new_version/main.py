# main.py

import os
import sys
import json
import time
import threading
from datetime import datetime

import psutil  # для проверки cs2.exe

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QPushButton,
    QVBoxLayout, QWidget, QHBoxLayout, QTextEdit, QLineEdit,
    QFileDialog, QDialog, QFormLayout, QCheckBox
)
from PyQt5.QtCore import QTimer

from bot_actions import CS2Bot
from launcher import (
    ToolPaths,
    start_with_proxifier_and_steam,
    run_memreduct,
    run_bes_limit,
    run_asf_send_all,
)

CONFIG_PATH = "accounts.json"


class BotThread(threading.Thread):
    """
    Фоновый поток «поведения» бота для одного аккаунта.
    Заходит в матч, имитирует активность, выходит и по кругу.
    """
    def __init__(self, stop_flag, window_title_hint="counter-strike 2",
                 startup_delay_sec=60, wait_for_cs2=True, play_minutes=10):
        super().__init__(daemon=True)
        self.stop_flag = stop_flag
        self.bot = CS2Bot(window_title_hint=window_title_hint)
        self.startup_delay_sec = startup_delay_sec
        self.wait_for_cs2 = wait_for_cs2
        self.play_minutes = play_minutes

    def _cs2_running(self) -> bool:
        try:
            for p in psutil.process_iter(["name"]):
                if (p.info.get("name") or "").lower() == "cs2.exe":
                    return True
        except Exception:
            pass
        return False

    def run(self):
        # 1) ждём появления cs2.exe (чтобы не мешать логину/guard)
        if self.wait_for_cs2:
            t0 = time.time()
            while not self.stop_flag.is_set() and time.time() - t0 < 900:
                if self._cs2_running():
                    break
                time.sleep(1.5)

        # 2) дополнительная пауза перед началом действий
        t1 = time.time()
        while not self.stop_flag.is_set() and time.time() - t1 < self.startup_delay_sec:
            time.sleep(0.5)

        # 3) основной цикл: матч -> играем -> выходим -> повтор
        while not self.stop_flag.is_set():
            try:
                if self.bot.ensure_in_match(search_timeout=240):
                    self.bot.play_loop(minutes=self.play_minutes)
                self.bot.leave_game()
                for _ in range(20):
                    if self.stop_flag.is_set():
                        break
                    time.sleep(0.5)
            except Exception:
                time.sleep(2.0)


class AccountDialog(QDialog):
    def __init__(self, parent=None, initial: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Добавить/изменить аккаунт")
        self.resize(560, 420)
        self._build()
        if initial:
            self.set_data(initial)

    def _build(self):
        self.le_proxifier = QLineEdit()
        self.btn_browse_prox = QPushButton("...")
        self.btn_browse_prox.clicked.connect(self._pick_proxifier)

        self.le_profile = QLineEdit()
        self.btn_browse_profile = QPushButton("...")
        self.btn_browse_profile.clicked.connect(self._pick_profile)

        self.le_steam = QLineEdit()
        self.btn_browse_steam = QPushButton("...")
        self.btn_browse_steam.clicked.connect(self._pick_steam)

        self.le_login = QLineEdit()
        self.le_pass = QLineEdit()
        self.le_pass.setEchoMode(QLineEdit.Password)

        self.cb_avast = QCheckBox("Запускать через Avast Sandbox")
        self.cb_type = QCheckBox("Фолбэк: печатать логин/пароль")

        self.le_box = QLineEdit()  # имя песочницы Sandboxie (например acc_1)

        form = QFormLayout()
        row = QWidget(); hl = QHBoxLayout(row); hl.addWidget(self.le_proxifier); hl.addWidget(self.btn_browse_prox)
        form.addRow("Proxifier.exe", row)

        row2 = QWidget(); hl2 = QHBoxLayout(row2); hl2.addWidget(self.le_profile); hl2.addWidget(self.btn_browse_profile)
        form.addRow("Профиль Proxifier (.ppx)", row2)

        row3 = QWidget(); hl3 = QHBoxLayout(row3); hl3.addWidget(self.le_steam); hl3.addWidget(self.btn_browse_steam)
        form.addRow("Steam.exe", row3)

        form.addRow("Логин Steam", self.le_login)
        form.addRow("Пароль Steam", self.le_pass)
        form.addRow("Имя песочницы (Sandboxie box)", self.le_box)
        form.addRow("", self.cb_avast)
        form.addRow("", self.cb_type)

        self.btn_ok = QPushButton("Сохранить")
        self.btn_ok.clicked.connect(self.accept)

        v = QVBoxLayout(self)
        v.addLayout(form)
        v.addWidget(self.btn_ok)

    def set_data(self, acc: dict):
        self.le_proxifier.setText(acc.get("proxifier_path", ""))
        self.le_profile.setText(acc.get("proxifier_profile", ""))
        self.le_steam.setText(acc.get("steam_path", ""))
        self.le_login.setText(acc.get("username", ""))
        self.le_pass.setText(acc.get("password", ""))  # да, храним в json как есть
        self.cb_avast.setChecked(bool(acc.get("use_avast", False)))
        self.cb_type.setChecked(bool(acc.get("type_credentials", False)))
        self.le_box.setText(acc.get("box_name", ""))

    def _pick_proxifier(self):
        path, _ = QFileDialog.getOpenFileName(self, "Proxifier.exe", "", "Executable (*.exe)")
        if path:
            self.le_proxifier.setText(path)

    def _pick_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Профиль Proxifier", "", "Profiles (*.ppx)")
        if path:
            self.le_profile.setText(path)

    def _pick_steam(self):
        path, _ = QFileDialog.getOpenFileName(self, "Steam.exe", "", "Executable (*.exe)")
        if path:
            self.le_steam.setText(path)

    def get_data(self):
        return {
            "proxifier_path": self.le_proxifier.text(),
            "proxifier_profile": self.le_profile.text(),
            "steam_path": self.le_steam.text(),
            "username": self.le_login.text(),
            "password": self.le_pass.text(),
            "use_avast": self.cb_avast.isChecked(),
            "type_credentials": self.cb_type.isChecked(),
            "box_name": self.le_box.text().strip(),
        }



class BotManager:
    def __init__(self):
        self.accounts = []
        self.processes = {}
        self.threads = {}
        self.tool_paths = ToolPaths()
        self.load_accounts()

    def update_account(self, idx: int, new_data: dict):
        if not (0 <= idx < len(self.accounts)):
            return
        # переносим служебные поля, чтобы не потерять статистику
        preserved = {
            "status": self.accounts[idx].get("status", "Stopped"),
            "last_run": self.accounts[idx].get("last_run", ""),
            "total_time": self.accounts[idx].get("total_time", 0),
            "cases_dropped": self.accounts[idx].get("cases_dropped", 0),
            "xp_earned": self.accounts[idx].get("xp_earned", 0),
        }
        self.accounts[idx] = {**new_data, **preserved}
        self.save_accounts()

    def load_accounts(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self.accounts = json.load(f)
        for acc in self.accounts:
            acc.setdefault("status", "Stopped")
            acc.setdefault("last_run", "")
            acc.setdefault("total_time", 0)
            acc.setdefault("cases_dropped", 0)
            acc.setdefault("xp_earned", 0)
            acc.setdefault("type_credentials", False)
            acc.setdefault("box_name", "")  # Sandboxie box

    def save_accounts(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.accounts, f, ensure_ascii=False, indent=2)

    def add_account(self, acc):
        self.accounts.append(acc)
        self.save_accounts()

    def remove_account(self, idx):
        if 0 <= idx < len(self.accounts):
            u = self.accounts[idx]["username"]
            self.stop_account(idx)
            del self.accounts[idx]
            self.save_accounts()
            return u

    def start_account(self, idx):
        if not (0 <= idx < len(self.accounts)):
            return
        acc = self.accounts[idx]

        # жёсткие проверки песочницы
        if not (self.tool_paths.sandboxie_start and os.path.exists(self.tool_paths.sandboxie_start)):
            print("[ERR] Sandboxie Start.exe не задан/не найден — запуск запрещён.")
            return
        if not acc.get("box_name"):
            print(f"[ERR] У аккаунта {acc.get('username')} не задан box_name — запуск запрещён.")
            return

        p = start_with_proxifier_and_steam(
            self.tool_paths,
            acc.get("proxifier_profile", ""),
            acc["steam_path"],
            acc["username"],
            acc["password"],
            use_avast_sandbox=False,               # игнорируем Avast
            width=1280, height=720, windowed=True,
            type_credentials=acc.get("type_credentials", False),
            box_name=acc.get("box_name", ""),
            require_sandbox=True,                  # принудительно через Sandboxie
        )
        self.processes[acc["username"]] = p
        acc["status"] = "Running"
        acc["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        # поток поведения бота
        stop_flag = threading.Event()
        title_hint = f"[{acc['box_name']}]" if acc.get("box_name") else "counter-strike 2"
        t = BotThread(stop_flag=stop_flag, window_title_hint=title_hint,
                      startup_delay_sec=60, wait_for_cs2=True, play_minutes=10)
        t.start()
        self.threads[acc["username"]] = (stop_flag, t)

    def stop_account(self, idx):
        if not (0 <= idx < len(self.accounts)):
            return
        acc = self.accounts[idx]
        u = acc["username"]

        # останавливаем поток бота
        if u in self.threads:
            self.threads[u][0].set()
            self.threads[u][1].join(timeout=2)
            del self.threads[u]

        # корректно завершаем песочницу, если есть box
        box = acc.get("box_name", "")
        if box and self.tool_paths.sandboxie_start and os.path.exists(self.tool_paths.sandboxie_start):
            try:
                subprocess.run(
                    [self.tool_paths.sandboxie_start, "/terminate", f"/box:{box}"],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
        else:
            # если по каким-то причинам запускали не через песочницу
            if u in self.processes:
                try:
                    if self.processes[u]:
                        self.processes[u].terminate()
                except Exception:
                    pass

        if u in self.processes:
            del self.processes[u]
        self.accounts[idx]["status"] = "Stopped"

    # системные утилиты (обёртки)
    def run_memreduct(self):
        return run_memreduct(self.tool_paths)

    def run_bes_limit(self):
        return run_bes_limit(self.tool_paths)

    def run_asf_send_all(self):
        return run_asf_send_all(self.tool_paths)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.m = BotManager()
        self._build_ui()
        self._refresh()

    def _edit(self, idx):
        # если аккаунт запущен — сначала останавливаем, чтобы не было гонок
        if self.m.accounts[idx].get("status") == "Running":
            self._log(f"Аккаунт {self.m.accounts[idx]['username']} запущен — останавливаю перед редактированием.")
            self._stop(idx)

        acc = self.m.accounts[idx]
        dlg = AccountDialog(self, initial=acc)
        if dlg.exec_():
            new_data = dlg.get_data()
            if not new_data.get("box_name"):
                self._log("ОШИБКА: укажи имя песочницы (box_name).")
                return
            if not all([new_data.get("steam_path"), new_data.get("username"), new_data.get("password")]):
                self._log("ОШИБКА: проверь Steam.exe / логин / пароль.")
                return

            self.m.update_account(idx, new_data)
            self._refresh()
            self._log(f"Аккаунт обновлён: {new_data['username']} (box={new_data['box_name']})")

    def _edit_selected(self):
        rows = self.table.selectionModel().selectedRows()
        for m in rows:
            self._edit(m.row())


    def _build_ui(self):
        self.setWindowTitle("CS2 Bot Farm Manager")
        self.resize(1200, 720)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Логин", "Статус", "Последний запуск", "Время", "Кейсы", "Опыт", "Действия"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        self.btn_add = QPushButton("Добавить аккаунт")
        self.btn_del = QPushButton("Удалить")
        self.btn_start = QPushButton("Старт")
        self.btn_stop = QPushButton("Стоп")
        self.btn_edit = QPushButton("Изменить")   # NEW

        self.btn_start_all = QPushButton("Старт все")
        self.btn_stop_all = QPushButton("Стоп все")

        self.btn_add.clicked.connect(self._add)
        self.btn_del.clicked.connect(self._del)
        self.btn_start.clicked.connect(self._start_selected)
        self.btn_stop.clicked.connect(self._stop_selected)
        self.btn_edit.clicked.connect(self._edit_selected)  # NEW

        self.btn_start_all.clicked.connect(self._start_all)
        self.btn_stop_all.clicked.connect(self._stop_all)

        self.btn_memreduct = QPushButton("MemReduct")
        self.btn_bes = QPushButton("BES")
        self.btn_asf = QPushButton("ASF")

        self.btn_memreduct.clicked.connect(
            lambda: self._log("MemReduct: " + ("OK" if self.m.run_memreduct() else "не найден"))
        )
        self.btn_bes.clicked.connect(
            lambda: self._log("BES открыт" if self.m.run_bes_limit() else "BES не найден")
        )
        self.btn_asf.clicked.connect(
            lambda: self._log("ASF запущен" if self.m.run_asf_send_all() else "ASF не найден")
        )

        # Поля путей инструментов
        self.le_prox = QLineEdit()
        self.le_sbie = QLineEdit()   # Sandboxie Start.exe
        self.le_avast = QLineEdit()
        self.le_mem = QLineEdit()
        self.le_bes = QLineEdit()
        self.le_asf = QLineEdit()
        for le, title in [
            (self.le_prox, "Proxifier.exe"),
            (self.le_sbie, "Sandboxie Start.exe"),
            (self.le_avast, "Avast sbox.exe"),
            (self.le_mem, "MemReduct.exe"),
            (self.le_bes, "BES.exe"),
            (self.le_asf, "ASF.exe"),
        ]:
            le.setPlaceholderText(title)

        self.btn_save_tools = QPushButton("Сохранить пути инструментов")
        self.btn_save_tools.clicked.connect(self._save_tools)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        top = QHBoxLayout()
        for b in (
            self.btn_add, self.btn_del, self.btn_start, self.btn_stop,
            self.btn_start_all, self.btn_stop_all,
            self.btn_memreduct, self.btn_bes, self.btn_asf,
        ):
            top.addWidget(b)

        tools = QHBoxLayout()
        for le in (self.le_prox, self.le_sbie, self.le_avast, self.le_mem, self.le_bes, self.le_asf):
            tools.addWidget(le)
        tools.addWidget(self.btn_save_tools)

        lay = QVBoxLayout()
        lay.addLayout(top)
        lay.addLayout(tools)
        lay.addWidget(self.table)
        lay.addWidget(self.log)

        w = QWidget()
        w.setLayout(lay)
        self.setCentralWidget(w)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.table.cellDoubleClicked.connect(lambda r, c: self._edit(r))  # NEW

        self.timer.start(3000)

    def _save_tools(self):
        self.m.tool_paths = ToolPaths(
            proxifier_exe=self.le_prox.text().strip(),
            avast_sandbox=self.le_avast.text().strip(),
            memreduct_exe=self.le_mem.text().strip(),
            bes_exe=self.le_bes.text().strip(),
            asf_exe=self.le_asf.text().strip(),
            sandboxie_start=self.le_sbie.text().strip(),  # обязателен
        )
        if not (self.m.tool_paths.sandboxie_start and os.path.exists(self.m.tool_paths.sandboxie_start)):
            self._log("ОШИБКА: укажи корректный путь к Sandboxie Start.exe — без него запуск запрещён.")
        else:
            self._log("Пути инструментов сохранены (Sandboxie OK)")

    def _log(self, msg):
        self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _refresh(self):
        self.table.setRowCount(len(self.m.accounts))
        for i, acc in enumerate(self.m.accounts):
            self.table.setItem(i, 0, QTableWidgetItem(acc["username"]))
            self.table.setItem(i, 1, QTableWidgetItem(acc.get("status", "Stopped")))
            self.table.setItem(i, 2, QTableWidgetItem(acc.get("last_run", "")))
            self.table.setItem(i, 3, QTableWidgetItem(self._fmt_time(acc.get("total_time", 0))))
            self.table.setItem(i, 4, QTableWidgetItem(str(acc.get("cases_dropped", 0))))
            self.table.setItem(i, 5, QTableWidgetItem(str(acc.get("xp_earned", 0))))

            cell = QWidget()
            h = QHBoxLayout(cell)
            h.setContentsMargins(0, 0, 0, 0)
            b1 = QPushButton("Старт")
            b2 = QPushButton("Стоп")
            b3 = QPushButton("Изм.")

            b1.clicked.connect(lambda _, idx=i: self._start(idx))
            b2.clicked.connect(lambda _, idx=i: self._stop(idx))
            b3.clicked.connect(lambda _, idx=i: self._edit(idx))  # NEW

            h.addWidget(b1);
            h.addWidget(b2);
            h.addWidget(b3);

            self.table.setCellWidget(i, 6, cell)

    @staticmethod
    def _fmt_time(s):
        h = s // 3600
        m = (s % 3600) // 60
        return f"{h}ч {m}м"

    def _add(self):
        d = AccountDialog(self)
        if d.exec_():
            data = d.get_data()
            if not data.get("box_name"):
                self._log("ОШИБКА: укажи имя песочницы (box_name) для аккаунта.")
                return
            if all([data.get("steam_path"), data.get("username"), data.get("password")]):
                self.m.add_account(data)
                self._refresh()
                self._log(f"Добавлен {data['username']} (box={data['box_name']})")

    def _del(self):
        rows = self.table.selectionModel().selectedRows()
        for m in rows:
            u = self.m.remove_account(m.row())
            if u:
                self._log(f"Удалён {u}")
        self._refresh()

    def _start(self, idx):
        self.m.start_account(idx)
        self._log(f"Запуск {self.m.accounts[idx]['username']}")

    def _stop(self, idx):
        self.m.stop_account(idx)
        self._log(f"Остановка {self.m.accounts[idx]['username']}")

    def _start_selected(self):
        for m in self.table.selectionModel().selectedRows():
            self._start(m.row())

    def _stop_selected(self):
        for m in self.table.selectionModel().selectedRows():
            self._stop(m.row())

    def _start_all(self):
        def run():
            for i in range(len(self.m.accounts)):
                self._log(f"Старт {self.m.accounts[i]['username']}")
                self.m.start_account(i)
                time.sleep(12)  # ступенчатый запуск
        threading.Thread(target=run, daemon=True).start()

    def _stop_all(self):
        for i in range(len(self.m.accounts)):
            self._stop(i)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
