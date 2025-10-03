import os                                                               # для операций с файлами
import shlex                                                            # для анализа синтаксиса оболочки Unix
import socket                                                           # получить имя хоста (компа)
import getpass                                                          # получить имя текущего пользователя
import sys
import argparse                                                         # для разбора параметров командной строки (--vfs, --prompt, --script)
import xml.etree.ElementTree as ET                                      # парсинг XML
import base64                                                           # для декодирования base64

def make_invite_line():
    """
    Формирование приглашения в виде username@hostname:cwd$
    Если cwd находится в домашней папке, показываем ~ вместо полного пути.
    """
    if params['prompt'] is not None:                                    # если есть пользовательский prompt
        return params['prompt'] + ' '                                   # возвращаем пользовательскую строку

    user = getpass.getuser()                                            # получение имя юзера системы
    host = socket.gethostname()                                         # получение имя хоста системы (компа)

    current_path = params.get('current_working_directory', ['root'])    # получение текущего пути, если None - root

    if current_path[:3] == ["root", "home", "user"]:                    # если путь начинается с домашней папки
        if len(current_path) > 3:                                       # если длина списка больше 3 эл
            display_path = "~/" + "/".join(current_path[3:])
        else:
            display_path = "~"
    elif current_path == ["root"]:                                      # если текущая папка - рут
        display_path = "/"
    else:
        display_path = "/" + "/".join(current_path[1:])                 # иначе просто соединяем все элементы через '/' от 1-го, т.к. первый -рут

    return f"{user}@{host}:{display_path}$ "                            # возврат приглашения в итоговом виде


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


def do_command(line):
    """
    Выполняет одну строку команды (сделал, чтобы можно было выполнять как из REPL, так и из скрипта).
    Возвращает True, если команда выполнена успешно и False, если произошла ошибка.
    """
    command_history.append(line)                                        # добавляем команду в историю

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

    elif command == "ls":                                               # вывод файлов и папок текущей директории
        handle_ls(args)

    elif command == "cd":                                               # смена рабочей директории
        handle_cd(args)

    elif command == "whoami":                                           # вывод имени пользователя
        handle_whoami(args)

    elif command == "history":                                          # вывод истории команд
        handle_history(args)

    elif command == "conf-dump":                                        # служебная команда для вывода конфигурации
        for key, value in params.items():
            print(f"{key} = {value}")

    elif command == "mv":                                               # перемещение/переименование объекта
        handle_mv(args)

    elif command == "chown":                                            # смена владельца объекта
        handle_chown(args)

    else:                                                               # если неизвестная команда — сообщаем об ошибке
        print(f"{command}: команда не найдена")
        return False

    return True


def run_script():
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

            print(make_invite_line() + line)                            # вывод строки с промптом приглашения, чтобы выглядело как ввод пользователя
            if not do_command(line):                                    # если выполнение команды завершилось ошибкой
                print("Ошибка во время исполнения стартового скрипта.")
                return False
    return True


def load_vfs():
    """
    Загружает VFS из XML-файла в память.
    Возвращает словарь с виртуальной файловой системой.
    """
    xml_path = params["vfs_path"]
    if not xml_path or not os.path.exists(xml_path):                    # если не указан путь или файл не существует
        print(f"Ошибка: файл VFS не найден: {xml_path}")                # выводим ошибку
        return None

    try:
        tree = ET.parse(xml_path)                                       # пытаемся разобрать XML-файл
        root_element = tree.getroot()                                   # получаем корневой элемент
    except ET.ParseError as e:                                          # если XML некорректный
        print(f"Ошибка: неверный формат XML VFS: {e}")                  # выводим ошибку
        return None


    def parse_folder(folder, owner='root'):                                           # рекурсивная функция, которая парсит папку за папкой в дереве иерархии
        current_folder = {
            "_type": 'folder',
            "_owner": owner
        }                                             # словарь хранения содержимого текущей папки
        for element in folder:
            name = element.attrib.get('name')
            if element.tag == 'folder':                                 # если элемент - папка
                current_folder[name] = parse_folder(element)
            if element.tag == 'file':                                   # если элемент - файл
                current_folder[name] = {
                    "_type": "file",
                    "_owner": owner,
                    # декодируем содержимое base64 в байтовую строку. element.text - содержимое тега, если оно пустое, тогда "" (вместо None)
                    "_content": base64.b64decode(element.text or "")
                }

        return current_folder

    vfs = {'root': parse_folder(root_element[0])}                       # парсим корневую папку, записываем в словарь root, т.к. при рекурсии она не учитывается
    return vfs                                                          # возвращаем словарь с vfs


def get_folder(path):
    """
    Возвращает словарь текущей папки внутри VFS по списку path.
    path — список папок от корня, вида *['root', 'home', 'user']
    """
    out_folder = params["vfs"]                                          # создаем аутпут папку и кладем туда vfs

    for folder in path:
        if folder not in out_folder or out_folder[folder]['_type'] != 'folder':      # если папки нет или она не является словарем
            return None
        out_folder = out_folder[folder]                                 # переходим в следующую папку

    return out_folder                                                   # возвращаем словарь искомой папки


def handle_ls(args):
    """
    ls - выводит содержимое текущей папки VFS
    """
    vfs = params['vfs']                                                 # получаем vfs из параметров
    if vfs is None:                                                     # если vfs не загружен
        print("Ошибка: VFS не загружен")
        return
    folder = get_folder(params["current_working_directory"])            # получаем словарь текущей папки
    for name, content in folder.items():                                # перебираем элементы текущей папки
        if name[0] == '_':
            continue
        if content['_type'] == "folder":                                # если элемент — папка (т.е. содержимое словарь)
            print(f'{name}/ (owner: {content["_owner"]})')              # обозначаем папку "/"
        else:                                                           # если элемент — файл
            print(f'{name} (owner: {content["_owner"]})')                                                 # выводим имя файла


def handle_cd(args):
    """
    cd — изменяет текущую виртуальную директорию внутри VFS.
    поддерживаются:
    - cd /          -> root
    - cd ~          -> root/home/user
    - cd ..         -> подняться на уровень выше (скип, если уже root)
    - cd <folder>   -> переход в подпапку
    - cd /<path>    -> абсолютный путь от root
    - cd ~/<path>   -> абсолютный путь от home/user
    """

    vfs = params['vfs']                                                 # получаем vfs из параметров
    if vfs is None:                                                     # если vfs не загружен
        print('Ошибка: VFS не загружен')
        return

    if len(args) == 1:                                                  # если путь не указан
        print('cd: не указан путь')
        return

    if len(args[1:]) > 1:                                               # если аргументов передано больше 1
        print(f'cd: много аргументов (ожидался 1, получено {len(args[1:])})')
        return

    target = args[1]                                                    # аргумент команды cd

    if target == '/':                                                   # абсолютный путь в корень
        params['current_working_directory'] = ['root']
        return

    elif target == '~':                                                 # домашняя папка
        params['current_working_directory'] = ['root', 'home', 'user']
        return

    elif target == '..':                                                # подняться на уровень выше
        if len(params['current_working_directory']) > 1:                # если мы не в руте
            params['current_working_directory'].pop()                   # удаляем последний элемент
        else:
            print('cd: уже в корне')
        return

    elif target[0] == '/':                                               # если указан абсолютный путь от корня
        parts = ["root"] + [i for i in target.split("/") if i]          # получаем список из папок переданного пути, if i для отброски пустой строки в начале
        folder = get_folder(parts)                                      # получаем искомую папку
        if folder is not None:                                          # если папка существует
            params['current_working_directory'] = parts                 # записываем ее в текущую рабочую папку
        else:
            print('cd: такого пути не существует')                      # иначе ошибка
        return

    elif target[0] == '~':                                               # аналогично абсолютному пути, только от домашней папки
        parts = ["root", "home", "user"] + [i for i in target.split("/") if i != '~'] # if i чтобы ~ в начале пустую строку
        folder = get_folder(parts)                                      # получаем искомую папку
        if folder is not None:                                          # если папка существует
            params['current_working_directory'] = parts                 # записываем ее в текущую рабочую папку
        else:
            print('cd: такого пути не существует')                      # иначе ошибка
        return

    else:                                                               # когда переход в подпапку
        current_folder = get_folder(params["current_working_directory"])# получаем словарь текущей рабочей папка

        if target in current_folder and isinstance(current_folder[target], dict): # если в текущей рабочей папке есть искомая и она словарь
            params['current_working_directory'].append(target)          # добавляем в путь эту папку
            return
        print('cd: папка не найдена')                                   # если не нашли - вывод ошибки


def handle_whoami(args):
    """
    whoami — выводит имя пользователя
    """
    user = getpass.getuser()                                            # получение имя юзера системы
    print(user)


def handle_history(args):
    """
    history — выводит историю команд по номерам
    """
    for index, command in enumerate(command_history):
        print(f'{index + 1} {command}')


def handle_mv(args):
    """
    mv <источник> <пункт назначения> — перемещает файл или папку внутри vfs
    также может переименовывать файл, если пункт назначения - файл а не папка
    """
    if len(args) != 3:                                                  # проверка количества аргументов (должно быть 3)
        print("mv: требуется два аргумента: <источник> <пункт назначения>")
        return

    source_path, destination_path = args[1], args[2]                    # исходный объект и новое имя/путь

    if source_path.startswith('/'):                                     # абсолютный путь источника
        source_parts = ["root"] + [i for i in source_path.split("/") if i]
    else:                                                               # относительный путь источника от текущей директори
        source_parts = params["current_working_directory"] + [i for i in source_path.split("/") if i]

    if destination_path.startswith('/'):                                # абсолютный путь объекта назначения
        destination_parts = ["root"] + [i for i in destination_path.split("/") if i]
    else:                                                               # относительный путь об. наз. от текущей директори
        destination_parts = params["current_working_directory"] + [i for i in destination_path.split("/") if i]

    source_folder = get_folder(source_parts[:-1])                       # папка исходного объекта
    source_name = source_parts[-1]                                      # имя исходного объекта
    destination_folder = get_folder(destination_parts[:-1])             # папка объекта назначения
    destination_name = destination_parts[-1]                            # имя объекта назначения

    if source_folder is None or source_name not in source_folder:       # если исходная папка не найдена или объекта нет в найденной папке
        print(f"mv: исходный объект {source_path} не найден")           # вывод ошибки
        return

    if destination_folder is None:                                      # если папка назначения не найдена
        print(f"mv: папка назначения {destination_path} не найдена")    # вывод ошибки
        return

    object = source_folder.pop(source_name)                             # получаем объект для переноса, при этом удаляя его из исходной папка

    if destination_name in destination_folder:                          # если объект назначения есть в папке назначения (файл или папка существует)
        destination_object = destination_folder[destination_name]       # получаем объект назначения (файл или папка)

        # если объект назначения - файл, а исходный - папка, то выдаем ошибку. Нельзя перенести папку в файл
        if isinstance(object, dict) and not isinstance(destination_object, dict):
            print(f"mv: нельзя переместить каталог '{source_path}' в файл '{destination_path}'")
            return

        if isinstance(destination_object, dict):                        # если объект назначения - папка
            destination_object[source_name] = object                    # в эту папку кладем объект переноса по имени (не важно папка или файл)
            print(f"{source_path} -> {destination_path} перемещено внутрь существующей папки")
        else:                                                           # если объект назначения - файл
            destination_folder[destination_name] = object               # то перезаписываем файл на файл для переноса
            print(f"{source_path} -> {destination_path}: перемещено и/или переименовано")
    else:                                                               # если объект назначения нет в папке назначения (файл или папка не существует)
        if '.' not in str(destination_name):                            # если новый объект назначения - папка
            destination_folder[destination_name] = {source_name: object}
        else:
            destination_folder[destination_name] = object               # если новый объект назначения - файл
        print(f"{source_path} -> {destination_path}: перемещено и/или переименовано")


def handle_chown(args):
    if len(args) != 3:                                                  # проверяем, что передано ровно 2 аргумента
        print('chown: требуется два аргумента: <пользователь> <путь к объекту>')
        return

    new_owner, path_str = args[1], args[2]                               # получаем имя нового владельца и путь к объекту

    if path_str.startswith('/'):                                        # путь от рута
        path_parts = ["root"] + [i for i in path_str.split("/") if i]
    else:                                                               # относительный путь от текущей директории
        path_parts = params["current_working_directory"] + [i for i in path_str.split("/") if i]

    parent_folder = get_folder(path_parts[:-1])                         # получаем папку, в которой находится объект
    name = path_parts[-1]                                               # имя объекта внутри этой папки

    if parent_folder is None or name not in parent_folder:              # если папка не существует или объект не найден
        print(f"chown: объект {path_str} не найден")
        return

    obj = parent_folder[name]                                           # получен объект
    obj["_owner"] = new_owner                                           # меняем владельца
    print(f"{path_str}: владелец изменён на {new_owner}")

def repl():
    """
    Основной цикл REPL.
    Принимает команды, парсит и выполняет логику.
    """
    while True:
        try:
            prompt = make_invite_line()                                 # формируем приглашение (стандарт или кастомное)
            line = input(prompt)                                        # принимаем строку от пользователя

            do_command(line)                                            # выполняем команду
        except KeyboardInterrupt:                                       # Ctrl+C — прерывание ввода.
            print("^C")
            continue
        except EOFError:                                                # Ctrl+Z — завершение оболочки
            print("\nexit")
            break
        except Exception as e:                                          # любая другая непредвиденная ошибка — сообщаем, но не завершаем
            print(f"Внутренняя ошибка: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()                                  # парсер аргументов вызываемый при старте файла

    parser.add_argument('--vfs', default=None)             # параметр --vfs - путь к VFS (по умолчанию текущая директория)
    parser.add_argument('--prompt', default=None)          # параметр --prompt: кастомное приглашение к вводу
    parser.add_argument('--script', default=None)          # параметр --script: путь к стартовому скрипту

    params_temp = parser.parse_args()                                   # получение параметров из командной строки

    params = {                                                          # собираем параметры в словарь
        'vfs_path': os.path.abspath(params_temp.vfs) if params_temp.vfs else None,  # абсолютный путь, если путь не указан - None
        'prompt': params_temp.prompt,
        'script_path': params_temp.script}
    command_history = []                                                # список, в котором будут храниться команды

    if params_temp.vfs != None:                                         # если путь к vfs указан
        vfs = load_vfs()                                                # загрузка vfs при старте эмулятора
        params['vfs'] = vfs                                             # сохраняем загруженную vfs в параметрах для дальнейшего использования
        params['current_working_directory'] = ['root']                  # записываем текущую рабочую папку
        print("Простой эмулятор оболочки по заданию 2")                 # отладочный вывод заданных параметров
    else:
        params['vfs'] = None                                            # если путь не указан, то vfs = None
        params['current_working_directory'] = ['root']                  # текущий путь root, но он нам не будет нужен

    if params['script_path'] is not None:                               # если установлен путь на скрипт, начинаем выполнять его
        if not run_script():                                            # если выполнение завершается ошибкой
            sys.exit(1)                                                 # завершаем программу

    repl()