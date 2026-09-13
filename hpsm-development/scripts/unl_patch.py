#!/usr/bin/env python3
"""
unl_patch.py — точечный патчер бинарных .unl файлов HPSM.

ВАЖНО, ЧЕСТНО ПРО УРОВЕНЬ УВЕРЕННОСТИ:
Формат .unl нигде публично не задокументирован по байтам. Всё, что делает этот
скрипт, основано ТОЛЬКО на разобранном по байтам реальном примере
(unload_test_SD.unl) и подтверждено сравнением байта длины с фактической длиной
строки. Подтверждена только одна вещь:

    [1 байт: длина строки N, 0..255] [N байт строки]

т.е. однобайтовый префикс длины перед строковыми значениями. Всё остальное в
файле (управляющие байты вроде 0x90, 0x91, 0x2f, 0x40 и т.д., структура
dbdict-заголовка, возможные внешние счётчики длины/контрольные суммы где-то
ещё в файле) НЕ расшифровано и НЕ проверяется этим скриптом.

Из-за этого скрипт умеет только одну безопасную операцию: заменить одно
известное строковое значение на другое, с корректным пересчётом байта длины,
и НИЧЕГО больше в файле не трогать. Если где-то в файле реально существует
внешний счётчик длины всей записи (мы этого не подтвердили, но и не
исключили) — после патча размер файла может не совпасть с тем, что
"ожидает" загрузчик. ПОЭТОМУ:

  1. Всегда работайте с копией, не с оригиналом.
  2. Всегда пробуйте загрузить патченный файл в тестовом/dev-инстансе SM,
     прежде чем доверять ему в проде.
  3. Если после патча загрузка ломается — это сигнал, что где-то есть
     нерасшифрованная нами зависимость, а не баг самого скрипта.

Использование:

  # посмотреть все распознанные length-prefixed строки в файле (только чтение)
  python3 unl_patch.py list input.unl

  # заменить одно или несколько значений и сохранить в новый файл
  python3 unl_patch.py patch input.unl output.unl \
      --set "test_SD=my_new_job_name" \
      --set "OSC=NEW_SERVICE_NAME"
"""

import argparse
import sys


def find_all(haystack: bytes, needle: bytes):
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx == -1:
            return
        yield idx
        start = idx + 1


def scan_strings(data: bytes, min_len: int = 3):
    """
    Только для чтения: эвристически находит байтовые последовательности вида
    [длина][печатаемые ASCII-байты этой длины] и возвращает их с оффсетом.

    Это НЕ гарантированно полный и НЕ гарантированно точный список полей —
    часть "находок" может быть случайным совпадением байтов внутри бинарных
    управляющих структур. Используйте как подсказку для человека/модели,
    не как авторитетный список полей файла.
    """
    results = []
    i = 0
    n = len(data)
    while i < n:
        length = data[i]
        if length >= min_len and i + 1 + length <= n:
            chunk = data[i + 1:i + 1 + length]
            if all(32 <= b <= 126 for b in chunk):
                try:
                    text = chunk.decode("ascii")
                    results.append((i, length, text))
                except UnicodeDecodeError:
                    pass
        i += 1
    return results


def patch_string_field(data: bytes, old_value: str, new_value: str, encoding: str = "utf-8") -> bytes:
    """
    Заменяет ОДНО length-prefixed строковое значение на другое.
    Требует, чтобы old_value встречался в файле с корректным байтом-длиной
    ровно один раз — иначе патч неоднозначен и лучше не гадать.
    """
    old_bytes = old_value.encode(encoding)
    new_bytes = new_value.encode(encoding)

    if len(old_bytes) > 255 or len(new_bytes) > 255:
        raise ValueError(
            "Подтверждена только однобайтовая схема длины (0-255 байт). "
            "Значение длиннее 255 байт использует неизвестную схему кодирования — "
            "патчить его этим скриптом небезопасно."
        )

    pattern = bytes([len(old_bytes)]) + old_bytes
    matches = list(find_all(data, pattern))

    if len(matches) == 0:
        raise ValueError(
            f"Значение {old_value!r} с корректным префиксом длины не найдено в файле. "
            f"Проверьте точное написание (регистр, пробелы) — используйте "
            f"'list', чтобы увидеть, что реально распознано."
        )
    if len(matches) > 1:
        raise ValueError(
            f"Значение {old_value!r} встречается {len(matches)} раз(а) с совпадающим "
            f"префиксом длины — патч неоднозначен. Уточните old_value (например, "
            f"включите больше окружающего текста), чтобы совпадение стало уникальным."
        )

    idx = matches[0]
    new_pattern = bytes([len(new_bytes)]) + new_bytes
    return data[:idx] + new_pattern + data[idx + len(pattern):]


def cmd_list(args):
    with open(args.file, "rb") as f:
        data = f.read()

    found = scan_strings(data, min_len=args.min_len)
    print(f"Найдено {len(found)} кандидатов (offset, length, text):")
    for offset, length, text in found:
        print(f"  0x{offset:06x}  len={length:3d}  {text!r}")
    print(
        "\nЭто эвристический список для чтения — часть строк может быть "
        "случайным совпадением бинарных байтов, а не реальным полем."
    )


def cmd_patch(args):
    with open(args.file, "rb") as f:
        data = f.read()

    for pair in args.set:
        if "=" not in pair:
            print(f"Пропускаю некорректный --set (нет '='): {pair}", file=sys.stderr)
            sys.exit(1)
        old_value, new_value = pair.split("=", 1)
        try:
            data = patch_string_field(data, old_value, new_value)
            print(f"OK: {old_value!r} -> {new_value!r}")
        except ValueError as e:
            print(f"ОШИБКА при замене {old_value!r} -> {new_value!r}: {e}", file=sys.stderr)
            sys.exit(1)

    with open(args.output, "wb") as f:
        f.write(data)

    print(f"\nСохранено: {args.output}")
    print("Не забудьте протестировать загрузку этого файла на dev-инстансе перед прод-использованием.")


def main():
    parser = argparse.ArgumentParser(description="Точечный патчер бинарных .unl файлов HPSM")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="Показать распознанные length-prefixed строки (только чтение)")
    p_list.add_argument("file", help="Путь к .unl файлу")
    p_list.add_argument("--min-len", type=int, default=3, help="Минимальная длина строки для показа (по умолчанию 3)")
    p_list.set_defaults(func=cmd_list)

    p_patch = sub.add_parser("patch", help="Заменить одно или несколько значений и сохранить в новый файл")
    p_patch.add_argument("file", help="Путь к исходному .unl файлу")
    p_patch.add_argument("output", help="Путь для сохранения патченного файла")
    p_patch.add_argument(
        "--set", action="append", default=[], required=True,
        metavar="OLD=NEW",
        help="Заменить значение OLD на NEW. Можно указывать несколько раз."
    )
    p_patch.set_defaults(func=cmd_patch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
