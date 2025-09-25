import os                                                               # для операций с файлами
import shlex                                                            # для анализа синтаксиса оболочки Unix
import socket                                                           # получить имя хоста
import getpass                                                          # получить имя текущего пользователя
import sys


def make_invite_line():
    """
    Формирование приглашения в виде username@hostname:cwd$
    Если cwd находится в домашней папке, показываем ~ вместо полного пути.
    """
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
        argv = shlex.split(line)                                        # shlex.split — инструмент для разбиения командной строки.
        return argv
    except ValueError as e:                                             # shlex.split() вызывает ValueError, когда входная строка некорректна
        raise SyntaxError(f"Ошибка разбора аргументов: {e}")


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
            prompt = make_invite_line()
            line = input(prompt)
            if not line.strip():                                        # пустая строка — просто показываем приглашение снова
                continue

            try:
                args = parse_command(line)
            except SyntaxError as e:                                    # Ошибка синтаксиса
                print(e)
                continue

            if not args:                                                # ничего не ввели после парсинга
                continue

            command = args[0]

            if command == "exit":                                       # Обработка команд
                print("exit")
                sys.exit(0)

            elif command == "ls":
                handle_ls(args)

            elif command == "cd":
                handle_cd(args)

            else:                                                       # Неизвестная команда — сообщение об ошибке
                print(f"{command}: команда не найдена")

        except KeyboardInterrupt:                                       # Ctrl+C — прерывание ввода.
            print("^C")
            continue
        except EOFError:                                                # Ctrl+D — завершение оболочки
            print("\nexit")
            break
        except Exception as e:                                          # Любая другая непредвиденная ошибка — сообщаем, но не завершаем
            print(f"Внутренняя ошибка: {e}")


if __name__ == "__main__":
    print("Простой эмулятор оболочки (минимальный прототип по заданию 1)")
    repl()