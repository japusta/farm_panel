import pyautogui
import time
import random
import sys
import logging

# Настройка логирования
logging.basicConfig(
    filename='steam_auto_login.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def human_like_delay(min_sec=0.1, max_sec=1.5):
    """Случайная задержка между действиями"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    return delay

def wait_for_element(image_path, timeout=30, confidence=0.7):
    """Ожидание появления элемента на экране"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            position = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if position:
                logging.info(f"Элемент найден: {image_path}")
                return position
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(1)
    logging.error(f"Элемент не найден: {image_path}")
    return None

def focus_steam_window():
    """Активация окна Steam"""
    try:
        # Поиск по заголовку окна (Windows)
        window = pyautogui.getWindowsWithTitle('Steam')
        if window:
            window[0].activate()
            logging.info("Окно Steam активировано")
            human_like_delay(1.0, 2.0)
            return True
    except Exception:
        pass
    return False

def steam_login(username, password):
    """Процесс авторизации в Steam"""
    try:
        logging.info("Начало авторизации в Steam")
        
        # Шаг 1: Активация окна Steam
        if not focus_steam_window():
            logging.warning("Не удалось найти окно Steam")
            return False

        # Шаг 2: Ожидание появления поля логина
        login_field = wait_for_element('steam_login_field.png', timeout=15)
        if not login_field:
            # Резервный вариант: клик по известным координатам
            pyautogui.click(500, 400)
            logging.warning("Использованы координаты для поля логина")
        else:
            pyautogui.click(login_field)
        
        # Шаг 3: Ввод логина
        human_like_delay(0.5, 1.0)
        pyautogui.write(username, interval=random.uniform(0.05, 0.2))
        logging.info(f"Введен логин: {username}")
        
        # Шаг 4: Переход к полю пароля
        human_like_delay(0.2, 0.5)
        pyautogui.press('tab')
        
        # Шаг 5: Ввод пароля
        human_like_delay(0.3, 0.8)
        pyautogui.write(password, interval=random.uniform(0.05, 0.15))
        logging.info("Пароль введен")
        
        # Шаг 6: Дополнительная случайная пауза перед подтверждением
        human_like_delay(0.5, 2.0)
        
        # Шаг 7: Отправка формы
        pyautogui.press('enter')
        logging.info("Форма отправлена")
        
        # Шаг 8: Ожидание завершения входа
        if wait_for_element('steam_guard_prompt.png', timeout=15):
            logging.warning("Требуется Steam Guard")
            return "steam_guard"
            
        if wait_for_element('steam_main_window.png', timeout=30):
            logging.info("Успешный вход в Steam")
            return True
        
        logging.error("Не удалось подтвердить вход")
        return False

    except Exception as e:
        logging.exception("Ошибка при авторизации:")
        return False

if __name__ == "__main__":
    # Пример использования
    USERNAME = "4dplesenb"
    PASSWORD = "Turuzmo3549!"
    
    result = steam_login(USERNAME, PASSWORD)
    
    if result is True:
        print("✅ Авторизация успешна")
    elif result == "steam_guard":
        print("⚠️ Требуется Steam Guard")
    else:
        print("❌ Ошибка авторизации")