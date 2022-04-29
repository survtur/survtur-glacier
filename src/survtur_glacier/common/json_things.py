import json
import gzip
import os
import random


def json_load(file: str):
    """
    Loads json.
    If file ends with .gz then opens it as gzip.
    """
    open_ = gzip.open if file.endswith(".gz") else open
    with open_(file, mode='tr', encoding='utf8') as f:
        return json.load(f)


def json_save(data, file: str, pretty: bool = True):
    """
    Saves JSON.
    If file ends with .gz then saves it as gzip-compressed.
    """
    if pretty:
        content = pretty_json(data)
    else:
        content = json.dumps(data)

    open_ = gzip.open if file.endswith(".gz") else open

    with open_(file, mode="tw", encoding="utf8") as f:
        print(content, file=f)


def json_dumps_compact(data, sort_keys: bool = False, **kwargs):
    """The most compact json representation"""
    return json.dumps(data,
                      ensure_ascii=False,
                      separators=(',', ':'),
                      sort_keys=sort_keys,
                      **kwargs)


def pretty_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent='\t')


def json_safe_save(data, file: str, pretty: bool = True):
    """
    Обеспечивает сохранность предыдущего файла в случае ошибки.
    Для этого сначала записывает во временный файл, а потом переименовывает.
    """
    temp = f"{file}~{str(random.random())}"
    json_save(data, temp, pretty)
    os.rename(temp, file)
