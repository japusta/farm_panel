# launcher.py
# Запуск Steam/CS2 (по аккаунту) строго через Sandboxie, с автологином и IMAP Steam Guard.
# Возвращает subprocess.Popen для внешнего менеджмента процессов.

import os
import subprocess
import time
import tempfile
import re
import imaplib
import email
import ctypes
import traceback
import socket
import ssl
from typing import Optional, Tuple

# === зависимости для ввода и поиска окна ===
try:
    import pyautogui
    HAVE_PYAUTO = True
except Exception:
    HAVE_PYAUTO = False

try:
    import win32gui, win32con
    HAVE_WIN32 = True
except Exception:
    HAVE_WIN32 = False


# ================== ВСПОМОГАТЕЛЬНЫЕ ОКНА ==================

def _msg(title: str, text: str):
    """Топ-модальное системное окно (поверх всего)."""
    MB_OK = 0x0
    MB_ICONINFO = 0x40
    MB_TOPMOST = 0x00040000
    MB_SYSTEMMODAL = 0x00001000
    try:
        ctypes.windll.user32.MessageBoxW(0, text, title, MB_OK | MB_ICONINFO | MB_TOPMOST | MB_SYSTEMMODAL)
    except Exception:
        print(f"[MSG] {title}: {text}")


# ================== ПУТИ И ИНСТРУМЕНТЫ ==================

class ToolPaths:
    def __init__(
        self,
        proxifier_exe: str = "",
        avast_sandbox: str = "",
        memreduct_exe: str = "",
        bes_exe: str = "",
        asf_exe: str = "",
        sandboxie_start: str = "",   # путь к Sandboxie Start.exe
    ):
        self.proxifier_exe = proxifier_exe
        self.avast_sandbox = avast_sandbox
        self.memreduct_exe = memreduct_exe
        self.bes_exe = bes_exe
        self.asf_exe = asf_exe
        self.sandboxie_start = sandboxie_start


def run_memreduct(paths: ToolPaths):
    if paths.memreduct_exe and os.path.exists(paths.memreduct_exe):
        subprocess.Popen([paths.memreduct_exe, "-EmptyStandbyList"])
        return True
    return False


def run_bes_limit(paths: ToolPaths):
    if paths.bes_exe and os.path.exists(paths.bes_exe):
        subprocess.Popen([paths.bes_exe])
        time.sleep(2)
        return True
    return False


def run_asf_send_all(paths: ToolPaths):
    if paths.asf_exe and os.path.exists(paths.asf_exe):
        subprocess.Popen([paths.asf_exe])
        return True
    return False


# ================== ОКНО STEAM ==================

def _find_steam_hwnd(timeout: float = 60.0) -> Optional[int]:
    """Ждём появления видимого окна Steam и возвращаем HWND."""
    if not HAVE_WIN32:
        return None
    t0 = time.time()
    while time.time() - t0 < timeout:
        hwnds = []
        def cb(h, _):
            if win32gui.IsWindowVisible(h):
                t = (win32gui.GetWindowText(h) or "").lower()
                if "steam" in t:
                    hwnds.append(h)
        win32gui.EnumWindows(cb, None)
        if hwnds:
            return hwnds[0]
        time.sleep(0.5)
    return None


def _activate_hwnd(hwnd) -> bool:
    if not HAVE_WIN32 or not hwnd:
        return False
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


# ================== ИНТЕРАКТИВНЫЙ ЗАХВАТ КООРДИНАТ ==================

def capture_coords_interactive(seconds: int = 5):
    """
    Даем по `seconds` сек на наведение мыши: логин → пароль → кнопка «Войти».
    Возвращает {"login":(x,y), "password":(x,y), "button":(x,y)}.
    """
    if not HAVE_PYAUTO:
        raise RuntimeError("pyautogui не установлен — не могу снять координаты")

    steps = [
        ("ПОЛЕ ЛОГИНА", "login"),
        ("ПОЛЕ ПАРОЛЯ", "password"),
        ("КНОПКУ «ВОЙТИ»", "button"),
    ]
    coords = {}
    for title, key in steps:
        _msg("Калибровка Steam",
             f"Наведи курсор на {title} и нажми OK.\n"
             f"После этого у тебя будет {seconds} сек, чтобы точно навести — координаты сниму автоматически.")
        for _ in range(seconds):
            time.sleep(1)
        x, y = pyautogui.position()
        coords[key] = (x, y)
        _msg("Калибровка Steam", f"{title}: X={x}, Y={y} — записано.")
    return coords


def capture_code_field_coord(seconds: int = 5) -> Tuple[int, int]:
    """Координата ПОЛЯ для кода Steam Guard."""
    _msg("Код Steam", f"Наведи курсор на ПОЛЕ ВВОДА КОДА и нажми OK.\n"
                      f"Даю {seconds} сек — координаты сниму автоматически.")
    for _ in range(seconds):
        time.sleep(1)
    if not HAVE_PYAUTO:
        raise RuntimeError("pyautogui недоступен")
    x, y = pyautogui.position()
    _msg("Код Steam", f"Поле кода: X={x}, Y={y} — записано.")
    return x, y


# ================== АВТОВВОД ПО КООРДИНАТАМ ==================

def create_autofill_script(username: str, password: str, coords: dict) -> str:
    """Генерируем .py, который вводит логин/пароль кликами по координатам."""
    lx, ly = coords["login"]
    px, py = coords["password"]
    bx, by = coords["button"]

    u = username.replace('"', '\\"')
    p = password.replace('"', '\\"')

    script_content = f'''
import pyautogui, time, sys, win32gui, win32con
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

def wait_steam(timeout=30):
    t = time.time()
    while time.time()-t < timeout:
        wins = []
        def cb(h,_):
            if win32gui.IsWindowVisible(h):
                t_ = (win32gui.GetWindowText(h) or "").lower()
                if "steam" in t_:
                    wins.append(h)
        win32gui.EnumWindows(cb, None)
        if wins:
            win32gui.ShowWindow(wins[0], win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(wins[0])
            return True
        time.sleep(0.5)
    return False

def main():
    if not wait_steam(): return False
    time.sleep(3.0)
    pyautogui.click({lx}, {ly}); time.sleep(1.0)
    pyautogui.hotkey('ctrl','a'); time.sleep(0.2)
    pyautogui.write("{u}", interval=0.10); time.sleep(1.0)

    pyautogui.click({px}, {py}); time.sleep(1.0)
    pyautogui.hotkey('ctrl','a'); time.sleep(0.2)
    pyautogui.write("{p}", interval=0.10); time.sleep(1.0)

    pyautogui.click({bx}, {by})
    return True

if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except Exception as e:
        print(e); sys.exit(1)
'''
    temp_dir = tempfile.gettempdir()
    script_path = os.path.join(temp_dir, f"steam_autofill_{int(time.time())}.py")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    return script_path


# ================== IMAP DEBUG/LOG ==================

def _make_imap_logger():
    log_path = os.path.join(tempfile.gettempdir(), f"steam_imap_{int(time.time())}.log")
    def _dbg(msg: str):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[IMAP] {ts} | {msg}"
        print(line, flush=True)
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
    _dbg(f"Лог IMAP: {log_path}")
    return _dbg, log_path

def _save_eml(eml_bytes: bytes, suffix="last"):
    try:
        path = os.path.join(tempfile.gettempdir(), f"steam_{suffix}_{int(time.time())}.eml")
        with open(path, "wb") as f:
            f.write(eml_bytes)
        return path
    except Exception:
        return None

def fetch_steam_email_code_imap(
    host: str,
    login: str,
    password: str,
    folder: str = "INBOX",
    timeout: int = 120,
    poll_interval: int = 5,
) -> Optional[str]:
    """
    Дебажная версия: подробно логирует каждый шаг и пытается несколько стратегий поиска.
    Сохраняет последнее найденное письмо в TEMP как *.eml.
    """
    dbg, _ = _make_imap_logger()

    # Быстрый сетевой тест до порта 993
    try:
        dbg(f"Проверка TCP к {host}:993 ...")
        with socket.create_connection((host, 993), timeout=10):
            dbg("TCP OK.")
    except Exception as e:
        dbg(f"TCP FAIL: {e}\n{traceback.format_exc()}")
        return None

    end = time.time() + timeout
    last_err = None

    try:
        import imaplib as _imaplib
        _imaplib.Debug = 0
    except Exception:
        pass

    while time.time() < end:
        try:
            dbg(f"Подключение к IMAP SSL: {host}:993 ...")
            ctx = ssl.create_default_context()
            with imaplib.IMAP4_SSL(host, 993, ssl_context=ctx) as M:
                dbg("Соединение установлено.")

                try:
                    sock = M.sock
                    cert = sock.getpeercert()
                    subj = dict(x[0] for x in cert.get("subject", (())))
                    dbg(f"SSL CN={subj.get('commonName')} | Issuer={cert.get('issuer')}")
                except Exception as e:
                    dbg(f"Не удалось прочитать сертификат: {e}")

                caps = []
                try:
                    typ, data = M.capability()
                    caps = (data or [b""])[0].decode("utf-8", "ignore").split()
                    dbg(f"CAPABILITY: {caps}")
                except Exception as e:
                    dbg(f"Ошибка CAPABILITY: {e}")

                try:
                    typ, data = M.login(login, password)
                    dbg(f"LOGIN -> {typ} {data}")
                    if typ != "OK":
                        dbg("Логин не OK. Проверь логин/пароль приложения/2FA/включение IMAP.")
                        return None
                except imaplib.IMAP4.error as e:
                    dbg(f"[AUTH] Ошибка аутентификации: {e}")
                    return None
                except Exception as e:
                    dbg(f"Иная ошибка логина: {e}\n{traceback.format_exc()}")
                    return None

                try:
                    typ, boxes = M.list()
                    dbg(f"LIST папок: typ={typ}, count={0 if not boxes else len(boxes)}")
                except Exception as e:
                    dbg(f"Ошибка LIST: {e}")

                typ, sel_data = M.select(folder, readonly=True)
                dbg(f"SELECT {folder} -> {typ} {sel_data}")
                if typ != "OK":
                    dbg(f"Не могу открыть папку {folder}. Проверь существование и права.")
                    return None

                searches = [
                    ('UNSEEN FROM "noreply@steampowered.com"', None),
                    ('OR FROM "noreply@steampowered.com" FROM "support@steampowered.com"', None),
                    ('HEADER SUBJECT "Steam Guard"', None),
                ]
                if any(cap.upper().startswith("X-GM-EXT-1") for cap in caps):
                    searches.insert(0, ('X-GM-RAW', 'from:noreply@steampowered.com newer_than:3d'))

                for q, arg in searches:
                    try:
                        if arg is None:
                            dbg(f"SEARCH {q} …")
                            typ, data = M.search(None, q)
                        else:
                            dbg(f"SEARCH {q} \"{arg}\" …")
                            typ, data = M.search(None, q, f'"{arg}"')
                        ids = data[0].split() if data and data[0] else []
                        dbg(f"Найдено писем: {len(ids)}")

                        if not ids:
                            continue

                        for msg_id in reversed(ids[-10:]):
                            dbg(f"FETCH msg_id={msg_id.decode() if isinstance(msg_id, bytes) else msg_id}")
                            typ, msg_data = M.fetch(msg_id, "(BODY.PEEK[] INTERNALDATE RFC822)")
                            if typ != "OK" or not msg_data or not msg_data[0]:
                                dbg(f"FETCH не OK: {typ} {msg_data}")
                                continue

                            raw = msg_data[0][1]
                            eml_path = _save_eml(raw, suffix="steam_last")
                            if eml_path:
                                dbg(f"Сохранил письмо в {eml_path}")

                            msg = email.message_from_bytes(raw)
                            subj = msg.get("Subject", "")
                            from_ = msg.get("From", "")
                            date_ = msg.get("Date", "")
                            dbg(f"Заголовки: From={from_} | Subject={subj} | Date={date_}")

                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    ctype = part.get_content_type()
                                    if ctype in ("text/plain", "text/html"):
                                        payload = part.get_payload(decode=True) or b""
                                        body += payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
                            else:
                                payload = msg.get_payload(decode=True) or b""
                                body = payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")

                            up = body.upper()
                            patterns = [
                                r"(STEAM\s*GUARD[^A-Z0-9]{0,100})([A-Z0-9]{5})",
                                r"(КОД[^0-9]{0,40})(\d{6})",
                                r"\b([A-Z0-9]{5})\b",
                                r"\b(\d{6})\b",
                            ]
                            code = None
                            for pat in patterns:
                                m = re.search(pat, up)
                                if m:
                                    code = m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)
                                    break

                            if code:
                                dbg(f"Код найден: {code}")
                                try:
                                    M.store(msg_id, "+FLAGS", "\\Seen")
                                except Exception as e:
                                    dbg(f"Не смог проставить \\Seen: {e}")
                                return code
                            else:
                                dbg("Код не найден в этом письме, продолжаю…")

                    except Exception as e:
                        last_err = e
                        dbg(f"Ошибка поиска {q}: {e}\n{traceback.format_exc()}")

                dbg("Пока нет кода. Жду новое письмо…")
                time.sleep(poll_interval)

        except Exception as e:
            last_err = e
            dbg(f"Исключение на верхнем уровне: {e}\n{traceback.format_exc()}")
            time.sleep(poll_interval)

    if last_err:
        dbg(f"Завершено по таймауту. Последняя ошибка: {last_err}")
    else:
        dbg("Завершено по таймауту без ошибок, но код не найден.")
    return None


def type_guard_code_at(x: int, y: int, code: str):
    """Вставляет код в поле и жмёт Enter."""
    if not HAVE_PYAUTO:
        return
    pyautogui.click(x, y)
    time.sleep(0.25)
    pyautogui.hotkey("ctrl", "a"); time.sleep(0.05)
    pyautogui.write(code, interval=0.08)
    time.sleep(0.2)
    pyautogui.press("enter")


# ================== ОСНОВНОЙ ЗАПУСК: ВСЕГДА ЧЕРЕЗ SANDBOXIE ==================

def start_with_proxifier_and_steam(
    paths: ToolPaths,
    proxifier_profile_ppx: str,
    steam_exe: str,
    username: str,
    password: str,
    use_avast_sandbox: bool = False,   # оставлен для совместимости, игнорируется
    width: int = 1280,
    height: int = 720,
    windowed: bool = True,
    type_credentials: bool = True,

    # калибровка координат логин/пароль/кнопка — даём пользователю навести мышь
    hover_capture_seconds: int = 5,

    # --- НАСТРОЙКИ IMAP ---
    enable_email_guard: bool = True,
    imap_host: str = "",          # напр. "imap.gmail.com"
    imap_login: str = "",         # адрес почты
    imap_password: str = "",      # пароль приложения (для Gmail)
    imap_folder: str = "INBOX",
    imap_timeout: int = 120,
    imap_poll_interval: int = 5,

    # --- SANDBOXIE ---
    box_name: str = "",
    require_sandbox: bool = True,  # требуем Sandboxie
) -> Optional[subprocess.Popen]:
    """
    Всегда запускает Steam/CS2 через Sandboxie (если require_sandbox=True).
    Возвращает Popen запуска (для внешнего менеджмента).
    """
    print(f"[RUN] __file__ = {__file__}")

    # === требуем песочницу ===
    if require_sandbox:
        if not (paths.sandboxie_start and os.path.exists(paths.sandboxie_start)):
            raise RuntimeError("Sandboxie обязательна: укажи корректный путь к Start.exe в настройках инструментов.")
        if not box_name:
            raise RuntimeError("Sandboxie обязательна: укажи имя песочницы (box_name) у аккаунта.")

    if not os.path.exists(steam_exe):
        raise FileNotFoundError(f"Steam.exe не найден: {steam_exe}")

    # гасим висящие процессы
    for exe in ("steam.exe", "steamwebhelper.exe", "cs2.exe"):
        try:
            subprocess.run(["taskkill", "/F", "/IM", exe],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    time.sleep(1)

    # Proxifier
    if (paths.proxifier_exe and os.path.exists(paths.proxifier_exe) and
        proxifier_profile_ppx and os.path.exists(proxifier_profile_ppx)):
        subprocess.Popen([paths.proxifier_exe, proxifier_profile_ppx, "/NoSplash"])
        time.sleep(3)

    # Steam args
    args = [steam_exe, "-applaunch", "730", "-novid", "-console"]
    if windowed:
        args += ["-windowed", "-noborder", "-w", str(width), "-h", str(height)]

    # ВСЕГДА через Sandboxie (без фолбэков)
    launch_cmd = [paths.sandboxie_start, f"/box:{box_name}", *args]

    print(f"Запускаем Steam (Sandboxie): {' '.join(launch_cmd)}")
    proc = subprocess.Popen(launch_cmd)

    # Ждём окно → активируем (не критично, если не нашли)
    hwnd = _find_steam_hwnd(timeout=60.0)
    if hwnd:
        _activate_hwnd(hwnd)
    else:
        _msg("Steam", "Окно Steam не найдено за 60 секунд. Продолжаю без активации окна.")

    # Калибровка координат и автозаполнение
    if type_credentials:
        if not HAVE_PYAUTO:
            print("[WARN] pyautogui недоступен — пропускаю автозаполнение.")
        else:
            coords = capture_coords_interactive(seconds=hover_capture_seconds)
            autofill_script = create_autofill_script(username, password, coords)
            print("Запускаем автозаполнение логина/пароля (в песочнице)…")

            # Всегда в том же боксе:
            autofill_proc = subprocess.Popen(
                [paths.sandboxie_start, f"/box:{box_name}", "python", autofill_script],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            try:
                autofill_proc.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                autofill_proc.kill()

    # === Ввод e-mail кода (IMAP) ===
    def _is_set(v: Optional[str]) -> bool:
        return isinstance(v, str) and v.strip() != ""

    print("[IMAP-GATE] enable_email_guard =", enable_email_guard)
    print("[IMAP-GATE] imap_host         =", repr(imap_host))
    print("[IMAP-GATE] imap_login        =", repr(imap_login))
    print("[IMAP-GATE] imap_password_set =", bool(imap_password and imap_password.strip()))

    if enable_email_guard and _is_set(imap_host) and _is_set(imap_login) and _is_set(imap_password):
        time.sleep(6)
        try:
            code_x, code_y = capture_code_field_coord(seconds=5)
        except Exception as e:
            print(f"[IMAP] Не удалось получить координату поля кода: {e}")
            return proc

        _msg("Код Steam", "Ищу письмо от Steam. Это может занять до 2 минут…")

        code = fetch_steam_email_code_imap(
            host=imap_host,
            login=imap_login,
            password=imap_password,
            folder=imap_folder,
            timeout=imap_timeout,
            poll_interval=imap_poll_interval,
        )
        if code:
            type_guard_code_at(code_x, code_y, code)
            _msg("Код Steam", f"Код «{code}» введён.")
        else:
            _msg("Код Steam", "Не удалось получить код из почты за отведённое время.")
    else:
        reasons = []
        if not enable_email_guard: reasons.append("enable_email_guard=False")
        if not _is_set(imap_host): reasons.append("imap_host пуст/пробелы")
        if not _is_set(imap_login): reasons.append("imap_login пуст/пробелы")
        if not _is_set(imap_password): reasons.append("imap_password пуст/пробелы")
        print(f"[email-guard] выключен или не заданы IMAP реквизиты. Причина: {', '.join(reasons) or 'неизвестно'}")

    print("Лаунчер завершил работу (основная последовательность).")
    return proc


# ---------- пример использования ----------
if __name__ == "__main__":
    paths = ToolPaths(
        proxifier_exe=r"C:\Program Files\Proxifier\Proxifier.exe",
        avast_sandbox=r"C:\Program Files\AVAST Software\Avast\AvastSbox.exe",
        memreduct_exe=r"C:\Program Files\Mem Reduct\memreduct.exe",
        bes_exe=r"C:\Program Files\BES\BES.exe",
        asf_exe=r"C:\ASF\ArchiSteamFarm.exe",
        sandboxie_start=r"D:\Sandboxie-Plus\Start.exe",
    )

    # Пример: запуск в песочнице acc_1; IMAP выключен
    start_with_proxifier_and_steam(
        paths=paths,
        proxifier_profile_ppx=r"C:\path\to\profile.ppx",
        steam_exe=r"D:\Steam\Steam.exe",
        username="login_here",
        password="password_here",
        use_avast_sandbox=False,
        width=960,
        height=540,
        windowed=True,
        type_credentials=False,
        enable_email_guard=True,
        imap_host="imap.gmail.com",
        imap_login="captainvacq@gmail.com",
        imap_password="oesdncouhmcbckro",   # для Gmail — пароль приложения
        imap_folder="INBOX",
        imap_timeout=120,
        imap_poll_interval=25,
        box_name="acc_1",
        require_sandbox=True,
    )


