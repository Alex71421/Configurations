import os                                                               # для операций с файлами
import shlex                                                            # для анализа синтаксиса оболочки Unix
import socket                                                           # получить имя хоста
import getpass                                                          # получить имя текущего пользователя
import sys
import argparse                                                         # для разбора параметров командной строки (--vfs, --prompt, --script)


def make_invite_line(params):
    """
    Формирование приглашения в виде username@hostname:cwd$
    Если cwd находится в домашней папке, показываем ~ вместо полного пути.
    """
    if params["prompt"] is not None:                                    # если есть пользовательский prompt
        return params["prompt"] + " "                                   # возвращаем пользовательскую строку

    user = getpass.getuser()
    host = socket.gethostname()
    cwd = os.getcwd()                                                   # current working directory
    home = os.path.expanduser("~")                                      # преобразует "~" в фактический путь

    if cwd == home or cwd.startswith(home + os.sep):                    # заменяем начальную часть домашним символом ~
        if cwd != home:
            display_cwd = '~' + cwd[len(home):]
        else:
            display_cwd = '~'
    else:                                                               # иначе оставляем как есть
        display_cwd = cwd

    return f"{user}@{host}:{display_cwd}$ "


def parse_command(line):
    """
    Парсинг строки команды в список аргументов.
    Возвращение списка argv. Если строка пустая — возвращается [].
    """
    try:
        args = shlex.split(line)                                        # shlex.split — инструмент для разбиения командной строки.
        return args
    except ValueError as e:                                             # shlex.split() вызывает ValueError, когда входная строка некорректна
        raise SyntaxError(f"Ошибка разбора аргументов: {e}")


def do_command(line, params):
    """
    Выполняет одну строку команды (сделал, чтобы можно было выполнять как из REPL, так и из скрипта).
    Возвращает True, если команда выполнена успешно и False, если произошла ошибка.
    """
    try:
        args = parse_command(line)                                      # разбираем строку на команды
    except SyntaxError as e:                                            # ошибка синтаксиса
        print(e)
        return False

    if not args:                                                        # ничего не ввели
        return True

    command = args[0]

    if command == "exit":                                               # обработка команд
        print("exit")
        sys.exit(0)

    elif command == "ls":
        handle_ls(args)

    elif command == "cd":
        handle_cd(args)

    elif command == "conf-dump":                                        # служебная команда для вывода конфигурации
        for key, value in params.items():
            print(f"{key} = {value}")

    else:                                                               # если неизвестная команда — сообщаем об ошибке
        print(f"{command}: команда не найдена")
        return False

    return True


def run_script(params):
    """
    Функция для выполнения стартового скрипта.
    Читает команды построчно и выполняет их, при первой ошибке выполнение прекращается.
    """
    script_path = params["script_path"]

    if not os.path.exists(script_path):                                 # если стартовый скрипт не найден по пути
        print(f"Ошибка: файл скрипта по пути {script_path} не найден")  # вывод ошибки
        return False

    with open(script_path, "r") as script:                              # открываем файл скрипта
        for line in script:                                             # построчно читаем файл
            line = line.strip()                                         # убираем лишние пробелы и \n

            if not line:                                                # пропускаем пустые строки
                continue

            print(make_invite_line(params) + line)                      # вывод строки с промптом приглашения, чтобы выглядело как ввод пользователя
            if not do_command(line, params):                            # если выполнение команды завершилось ошибкой
                print("Ошибка во время исполнения стартового скрипта.")
                return False
    return True



def handle_ls(args):
    """
    Заглушка для команды ls.
    """
    print(f"ls called with args: {args[1:]}")


def handle_cd(args):
    """
    Заглушка для команды cd.
    """
    path = args[1:]
    if len(path) > 1:
        print("cd: много аргументов (ожидалось 0 или 1)")
    else:
        print(f"cd called with args: {path}")


def repl():
    """
    Основной цикл REPL.
    Принимает команды, парсит и выполняет логику.
    """
    while True:
        try:
            prompt = make_invite_line(params)                           # формируем приглашение (стандарт или кастомное)
            line = input(prompt)                                        # принимаем строку от пользователя

            if not do_command(line, params):                            # выполняем команду, если завершена с ошибкой
                continue                                                # продолжаем цикл
        except KeyboardInterrupt:                                       # Ctrl+C — прерывание ввода.
            print("^C")
            continue
        except EOFError:                                                # Ctrl+D — завершение оболочки
            print("\nexit")
            break
        except Exception as e:                                          # любая другая непредвиденная ошибка — сообщаем, но не завершаем
            print(f"Внутренняя ошибка: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()                                  # парсер аргументов вызываемый при старте файла

    parser.add_argument("--vfs", default=os.getcwd())      # параметр --vfs - путь к VFS (по умолчанию текущая директория)
    parser.add_argument("--prompt", default=None)          # параметр --prompt: кастомное приглашение к вводу
    parser.add_argument("--script", default=None)          # параметр --script: путь к стартовому скрипту

    params_temp = parser.parse_args()                                   # получение параметров из командной строки

    params = {                                                          # собираем параметры в словарь
        "vfs_path": os.path.abspath(params_temp.vfs),                   # абсолютный путь
        "prompt": params_temp.prompt,
        "script_path": params_temp.script}

    print("Простой эмулятор оболочки по заданию 2")                     # отладочный вывод заданных параметров

    if params["script_path"] is not None:                               # если установлен путь на скрипт, начинаем выполнять его
        if not run_script(params):                                      # если выполнение завершается ошибкой
            sys.exit(1)                                                 # завершаем программу

    repl()