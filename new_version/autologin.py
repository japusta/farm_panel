import pyautogui
import time

# ===== НАСТРОЙКИ =====
STEAM_LOGIN = "4dplesenb"     # Ваш логин Steam
STEAM_PASSWORD = "Turuzmo3549!"  # Ваш пароль Steam

# Координаты полей (настроено под ваш экран)
LOGIN_FIELD_X = 720   # X координата поля логина
LOGIN_FIELD_Y = 406   # Y координата поля логина
PASSWORD_FIELD_X = 583 # X координата поля пароля  
PASSWORD_FIELD_Y = 513 # Y координата поля пароля
LOGIN_BUTTON_X = 815   # X координата кнопки входа (примерно под полем пароля)
LOGIN_BUTTON_Y = 635   # Y координата кнопки входа (чуть ниже поля пароля)

DELAY = 1  # Задержка между действиями (секунды)

def find_mouse_position():
    """Помогает найти координаты элементов"""
    print("Наведите мышь на нужный элемент и посмотрите координаты:")
    print("Нажмите Ctrl+C для остановки")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"\rКоординаты мыши: X={x}, Y={y}", end="")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nГотово!")

def steam_auto_login():
    """Основная функция автозаполнения"""
    print("=== Автозаполнение Steam ===")
    print("Убедитесь, что окно Steam открыто и видно")
    print("Запуск через 3 секунды...")
    
    # Обратный отсчет
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    
    try:
        # Отключаем защиту от случайных движений мыши
        pyautogui.FAILSAFE = True
        
        print("Заполняем поле логина...")
        # Клик по полю логина
        pyautogui.click(LOGIN_FIELD_X, LOGIN_FIELD_Y)
        time.sleep(DELAY)
        
        # Очищаем поле и вводим логин
        pyautogui.hotkey('ctrl', 'a')  # Выделить все
        time.sleep(0.2)
        pyautogui.write(STEAM_LOGIN)   # Ввести логин
        time.sleep(DELAY)
        
        print("Заполняем поле пароля...")
        # Клик по полю пароля
        pyautogui.click(PASSWORD_FIELD_X, PASSWORD_FIELD_Y)
        time.sleep(DELAY)
        
        # Очищаем поле и вводим пароль
        pyautogui.hotkey('ctrl', 'a')  # Выделить все
        time.sleep(0.2)
        pyautogui.write(STEAM_PASSWORD) # Ввести пароль
        time.sleep(DELAY)
        
        print("Нажимаем кнопку входа...")
        # Клик по кнопке входа
        pyautogui.click(LOGIN_BUTTON_X, LOGIN_BUTTON_Y)
        
        print("Автозаполнение завершено!")
        
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        print("Убедитесь, что координаты настроены правильно")

def main():
    """Главное меню"""
    while True:
        print("\n=== Steam Auto-Login ===")
        print("1. Запустить автозаполнение")
        print("2. Найти координаты элементов")
        print("3. Показать текущие настройки")
        print("4. Выход")
        
        choice = input("\nВыберите действие (1-4): ")
        
        if choice == "1":
            steam_auto_login()
        elif choice == "2":
            find_mouse_position()
        elif choice == "3":
            print(f"\n--- Текущие настройки ---")
            print(f"Логин: {STEAM_LOGIN}")
            print(f"Пароль: {'*' * len(STEAM_PASSWORD)}")
            print(f"Поле логина: X={LOGIN_FIELD_X}, Y={LOGIN_FIELD_Y}")
            print(f"Поле пароля: X={PASSWORD_FIELD_X}, Y={PASSWORD_FIELD_Y}")
            print(f"Кнопка входа: X={LOGIN_BUTTON_X}, Y={LOGIN_BUTTON_Y}")
            print(f"Задержка: {DELAY} сек")
        elif choice == "4":
            print("До свидания!")
            break
        else:
            print("Неверный выбор!")

if __name__ == "__main__":
    main()