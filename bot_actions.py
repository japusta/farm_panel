import time
import random
import pyautogui
import cv2
import numpy as np

class CS2Bot:
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.center_x = self.screen_width // 2
        self.center_y = self.screen_height // 2
    
    def random_movement(self):
        """Случайные движения персонажа"""
        actions = [
            {'key': 'w', 'duration': random.uniform(1.0, 3.0)},
            {'key': 'a', 'duration': random.uniform(0.5, 1.5)},
            {'key': 's', 'duration': random.uniform(0.5, 1.0)},
            {'key': 'd', 'duration': random.uniform(1.0, 2.0)},
            {'key': 'space', 'duration': 0.1},
        ]
        
        # Выполняем 5-10 случайных действий
        for _ in range(random.randint(5, 10)):
            action = random.choice(actions)
            pyautogui.keyDown(action['key'])
            time.sleep(action['duration'])
            pyautogui.keyUp(action['key'])
            
            # Случайные паузы между действиями
            time.sleep(random.uniform(0.1, 1.5))
            
            # Случайное движение мыши
            self.random_mouse_movement()
            
            # Случайный выстрел
            if random.random() > 0.7:
                self.random_shot()
    
    
    def random_mouse(self):
        dx = random.randint(-120, 120)
        dy = random.randint(-120, 120)
        dur = random.uniform(0.2, 0.8)
        pyautogui.moveRel(dx, dy, duration=dur)

    def random_keys(self):
        actions = [
            ("w", random.uniform(1.0, 2.5)),
            ("a", random.uniform(0.6, 1.3)),
            ("s", random.uniform(0.5, 1.0)),
            ("d", random.uniform(0.6, 1.6)),
        ]
        k, d = random.choice(actions)
        pyautogui.keyDown(k); time.sleep(d); pyautogui.keyUp(k)
    
    def random_mouse_movement(self):
        """Случайное движение мыши с плавной анимацией"""
        dx = random.randint(-100, 100)
        dy = random.randint(-100, 100)
        duration = random.uniform(0.2, 1.0)
        steps = int(duration * 10)
        
        for _ in range(steps):
            pyautogui.moveRel(dx//steps, dy//steps, duration=duration/steps)
    
    def random_shot(self):
        if random.random() < 0.35:
            dur = random.uniform(0.08, 0.25)
            pyautogui.mouseDown(button="left")
            time.sleep(dur)
            pyautogui.mouseUp(button="left")
    
    def detect_main_menu(self):
        """Обнаружение главного меню по характерным элементам"""
        screenshot = pyautogui.screenshot()
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Поиск кнопки "PLAY" (пример)
        play_template = cv2.imread('play_button.png', 0)
        if play_template is not None:
            res = cv2.matchTemplate(
                cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 
                play_template, 
                cv2.TM_CCOEFF_NORMED
            )
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            if max_val > 0.8:
                return True
        
        return False
    
    def join_game(self):
        """Вход в игру через главное меню"""
        if self.detect_main_menu():
            # Нажимаем кнопку PLAY
            pyautogui.click(x=self.center_x, y=self.center_y + 100)
            time.sleep(2)
            
            # Выбираем режим Casual
            pyautogui.click(x=self.center_x - 100, y=self.center_y)
            time.sleep(1)
            
            # Подтверждаем выбор
            pyautogui.click(x=self.center_x, y=self.center_y + 200)
            time.sleep(10)
            
            return True
        return False
    
    def leave_game(self):
        """Выход из текущего матча"""
        pyautogui.press('esc')
        time.sleep(1)
        pyautogui.click(x=self.center_x - 100, y=self.center_y + 200)  # Disconnect
        time.sleep(10)

    def tick(self):
        """Один «тик» поведения: немного двигаемся, мышь, иногда выстрел."""
        self.random_keys()
        time.sleep(random.uniform(0.15, 0.6))
        self.random_mouse()
        self.random_shot()