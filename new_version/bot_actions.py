# bot_actions.py
# Действия бота внутри CS2: фокус окна, анти-AFK, "человечные" паттерны,
# старт/поиск/принятие матча, игровая сессия и выход.
#
# Файл дружит с Sandboxie: если в ini включён BoxNameTitle=y, можно
# передавать в конструктор window_title_hint вида "[acc_1]".

import os
import time
import random
from typing import Optional, Tuple, List

# --- зависимости ---
import pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.08  # небольшая пауза между действиями

try:
    import cv2
    import numpy as np
    HAVE_CV = True
except Exception:
    HAVE_CV = False


class CS2Bot:
    def __init__(self, window_title_hint: str = "counter-strike 2"):
        self.window_title_hint = (window_title_hint or "counter-strike 2").lower()
        self.screen_width, self.screen_height = pyautogui.size()
        self.center_x = self.screen_width // 2
        self.center_y = self.screen_height // 2

        # базовые амплитуды
        self.small_move = 60
        self.medium_move = 160
        self.big_move = 320

    # ==================== УТИЛИТЫ ====================

    def _human_sleep(self, a: float, b: float):
        time.sleep(random.uniform(a, b))

    def _rand_point_near(self, x: int, y: int, spread: int = 6) -> Tuple[int, int]:
        return x + random.randint(-spread, spread), y + random.randint(-spread, spread)

    def _press(self, key: str, dur: float = 0.0):
        if dur > 0:
            pyautogui.keyDown(key)
            time.sleep(dur)
            pyautogui.keyUp(key)
        else:
            pyautogui.press(key)

    # ==================== ФОКУС ОКНА ====================

    def focus_window(self) -> bool:
        """
        Мягкий фокус окна по заголовку.
        Если win32 доступен — ищем видимое окно с self.window_title_hint в заголовке.
        Иначе — Alt+Tab и клик в центр.
        """
        try:
            import win32gui
            import win32con
            hint = self.window_title_hint
            hwnds: List[int] = []

            def cb(h, _):
                if win32gui.IsWindowVisible(h):
                    t = (win32gui.GetWindowText(h) or "").lower()
                    if hint in t:
                        hwnds.append(h)

            win32gui.EnumWindows(cb, None)
            if hwnds:
                win32gui.ShowWindow(hwnds[0], win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnds[0])
                return True
        except Exception:
            pass

        # fall back
        try:
            pyautogui.keyDown("alt"); pyautogui.press("tab"); pyautogui.keyUp("alt")
            self._human_sleep(0.2, 0.4)
            pyautogui.click(self.center_x, self.center_y)
            return True
        except Exception:
            return False

    # ==================== СКРИНШОТ/ШАБЛОНЫ ====================

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None):
        im = pyautogui.screenshot(region=region)
        if not HAVE_CV:
            return im  # PIL Image
        img = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
        return img

    def _match_template(
        self,
        haystack_bgr,
        needle_bgr,
        threshold: float = 0.85,
        scales: Tuple[float, ...] = (1.0, 0.9, 0.8),
        method: int =  cv2.TM_CCOEFF_NORMED if HAVE_CV else 0,
    ) -> Optional[Tuple[int, int, int, int, float]]:
        """
        Ищет needle на haystack с несколькими масштабами.
        Возвращает (x, y, w, h, score) в координатах haystack или None.
        """
        if not HAVE_CV:
            return None

        hs = cv2.cvtColor(haystack_bgr, cv2.COLOR_BGR2GRAY)
        nd = cv2.cvtColor(needle_bgr, cv2.COLOR_BGR2GRAY)

        best = None
        for s in scales:
            nds = nd if s == 1.0 else cv2.resize(nd, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            if nds.shape[0] < 5 or nds.shape[1] < 5:
                continue

            res = cv2.matchTemplate(hs, nds, method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            # нормируем
            score = max_val
            loc = max_loc

            if score >= threshold:
                h, w = nds.shape[:2]
                x, y = loc
                cand = (x, y, w, h, score)
                if (best is None) or (cand[-1] > best[-1]):
                    best = cand

        return best

    def find_and_click(
        self,
        template_path: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        threshold: float = 0.86,
        click_offset: Tuple[int, int] = (0, 0),
        jitter: int = 4,
    ) -> bool:
        """
        Ищет картинку и кликает по центру совпадения.
        """
        if not HAVE_CV or not os.path.exists(template_path):
            return False

        hay = self.screenshot(region)
        needle = cv2.imread(template_path, cv2.IMREAD_COLOR)
        m = self._match_template(hay, needle, threshold=threshold)
        if not m:
            return False
        x, y, w, h, _ = m
        cx, cy = x + w // 2, y + h // 2
        if region:
            rx, ry, _, _ = region
            cx += rx; cy += ry
        cx, cy = self._rand_point_near(cx + click_offset[0], cy + click_offset[1], jitter)
        pyautogui.click(cx, cy)
        return True

    # ==================== БАЗОВЫЕ "ЧЕЛОВЕЧНЫЕ" ДЕЙСТВИЯ ====================

    def random_movement(self, min_d: float = 0.8, max_d: float = 2.2):
        seq = ['w', 'a', 's', 'd']
        random.shuffle(seq)
        for key in seq:
            dur = random.uniform(min_d, max_d)
            pyautogui.keyDown(key)
            self._human_sleep(dur * 0.6, dur)
            pyautogui.keyUp(key)
            self._human_sleep(0.05, 0.25)

    def random_look(self):
        dx = random.choice([-1, 1]) * random.randint(self.small_move, self.medium_move)
        dy = random.choice([-1, 1]) * random.randint(10, 60)
        steps = random.randint(8, 16)
        for _ in range(steps):
            px = int(dx / steps + random.uniform(-1.5, 1.5))
            py = int(dy / steps + random.uniform(-1.2, 1.2))
            pyautogui.moveRel(px, py, duration=random.uniform(0.010, 0.035))
        self._human_sleep(0.05, 0.15)

    def random_jump_crouch(self):
        if random.random() < 0.5:
            self._press('space')  # jump
        if random.random() < 0.4:
            self._press('ctrl', dur=random.uniform(0.05, 0.20))
        if random.random() < 0.35:
            self._press('shift', dur=random.uniform(0.20, 0.60))
        self._human_sleep(0.05, 0.20)

    def random_shot(self):
        dur = random.uniform(0.05, 0.35)
        pyautogui.mouseDown(button='left')
        time.sleep(dur)
        pyautogui.mouseUp(button='left')

    def micro_actions(self):
        if random.random() < 0.2:
            pyautogui.press('r')  # reload
        if random.random() < 0.15:
            pyautogui.press('tab')  # scoreboard
        if random.random() < 0.1:
            pyautogui.press('g')  # иногда дроп
        if random.random() < 0.15:
            pyautogui.scroll(random.choice([-1, 1]) * random.randint(1, 3))
        self._human_sleep(0.05, 0.20)

    # ==================== НАВИГАЦИЯ МЕНЮ ====================

    def detect_main_menu(self) -> bool:
        """
        Эвристика: нажмём ESC (открыть меню), затем попытаемся кликнуть кнопку Play по ассету
        (assets/play_btn.png), если ассета нет — попробуем типовой клик по координатам.
        """
        pyautogui.press('esc')
        self._human_sleep(0.4, 0.7)

        tpl = os.path.join("assets", "play_btn.png")
        if HAVE_CV and os.path.exists(tpl):
            if self.find_and_click(tpl, threshold=0.80):
                self._human_sleep(0.8, 1.4)
                return True

        # фолбэк: клик "Play" в типовой зоне
        pyautogui.click(self.center_x, self.center_y + 260)
        self._human_sleep(0.5, 1.0)
        return True

    def start_match_search(self) -> bool:
        """
        Запуск поиска матча: ESC → Play → вкладка (если есть) → Start.
        С ассетами (assets/premier_tab.png, assets/start_btn.png) или через координаты.
        """
        self.detect_main_menu()

        # ассеты, если есть
        used_assets = False
        mapping = [
            ("assets/play_btn.png", 0.80),
            ("assets/premier_tab.png", 0.82),  # или casual/dm
            ("assets/start_btn.png", 0.82),
        ]
        for path, thr in mapping:
            if HAVE_CV and os.path.exists(path):
                if self.find_and_click(path, threshold=thr):
                    used_assets = True
                    self._human_sleep(0.5, 1.0)

        if used_assets:
            return True

        # фолбэк по координатам
        # Play уже нажали в detect_main_menu; выберем вкладку и старт
        pyautogui.click(self.center_x - 420, self.center_y - 200)  # вкладка
        self._human_sleep(0.5, 0.8)
        pyautogui.click(self.center_x, self.center_y + 320)        # Start
        self._human_sleep(1.2, 2.0)
        return True

    def accept_match_if_found(self, wait_sec: int = 120) -> bool:
        """
        Ждём всплывашку "ACCEPT" и жмём её (по ассету или Enter).
        """
        end = time.time() + wait_sec
        tpl = os.path.join("assets", "accept_btn.png")
        while time.time() < end:
            if HAVE_CV and os.path.exists(tpl):
                if self.find_and_click(tpl, threshold=0.82):
                    self._human_sleep(0.5, 1.0)
                    return True
            # фолбэк — иногда можно подтвердить Enter
            pyautogui.press('enter')
            self._human_sleep(0.8, 1.5)
        return False

    # ==================== ВЫСОКОУРОВНЕВЫЕ СЦЕНАРИИ ====================

    def ensure_in_match(self, search_timeout: int = 240) -> bool:
        """
        Гарантирует, что мы попадём в матч: фокус окна → старт поиска → ожидание accept → ждём загрузки.
        """
        self.focus_window()
        self.start_match_search()

        # ждём появления переговорной (accept):
        self.accept_match_if_found(wait_sec=max(30, search_timeout))

        # ждём загрузку карты (просто подождём/повзаимодействуем)
        t0 = time.time()
        while time.time() - t0 < 45:
            # крутим камеру/жмём W, чтобы пройти разминку/заморозку
            pyautogui.keyDown('w'); self._human_sleep(0.3, 0.6); pyautogui.keyUp('w')
            self.random_look()
            if random.random() < 0.25:
                self.random_jump_crouch()
        return True

    def play_loop(self, minutes: int = 10):
        """
        Игровая сессия. Действия перемешаны, чтобы не было очевидных циклов.
        """
        end = time.time() + max(1, minutes) * 60
        while time.time() < end:
            self.focus_window()
            # микс
            self.random_movement()
            if random.random() < 0.8:
                self.random_look()
            if random.random() < 0.35:
                self.random_shot()
            if random.random() < 0.5:
                self.micro_actions()
            if random.random() < 0.25:
                self.random_jump_crouch()
            self._human_sleep(0.2, 0.6)

    def leave_game(self):
        """
        Корректный выход:
        - пробуем ESC → клик по кнопке Leave (если есть ассет assets/leave_btn.png)
        - фолбэк: ESC → два клика в типовые области (кнопка Leave и подтверждение)
        - в крайнем случае пробуем консоль 'disconnect' (если открывается '~')
        """
        self.focus_window()
        pyautogui.press('esc')
        self._human_sleep(0.4, 0.8)

        tpl = os.path.join("assets", "leave_btn.png")
        if HAVE_CV and os.path.exists(tpl) and self.find_and_click(tpl, threshold=0.82):
            self._human_sleep(0.5, 0.9)
            # подтверждение, если всплывает
            tpl2 = os.path.join("assets", "confirm_btn.png")
            if HAVE_CV and os.path.exists(tpl2):
                self.find_and_click(tpl2, threshold=0.82)
            else:
                # фолбэк подтверждения
                pyautogui.click(self.center_x + 180, self.center_y + 160)
            return

        # координатный фолбэк: область кнопки Leave и подтверждение
        pyautogui.click(self.center_x + 260, self.center_y + 180)  # Leave
        self._human_sleep(0.4, 0.8)
        pyautogui.click(self.center_x + 180, self.center_y + 160)  # Confirm

        # попытка консольного выхода (если включена -console)
        if random.random() < 0.2:
            pyautogui.press('`')  # тильда / ё
            self._human_sleep(0.2, 0.4)
            pyautogui.typewrite("disconnect", interval=0.03)
            pyautogui.press('enter')

    # совместимость со старым циклом
    def tick(self):
        """Лёгкий анти-AFK тик (на случай старых сценариев вызова)."""
        self.focus_window()
        actions = [
            self.random_movement,
            self.random_look,
            self.random_jump_crouch,
            self.random_shot,
            self.micro_actions,
        ]
        random.choice(actions)()
