from typing import Union
import math


def hr_int(v: int):
    sign = '-' if v < 0 else ''
    v = abs(v)
    if v < 1000:
        s = str(v)
    elif v < 100000:
        s = f'{v / 1000:0.1f}k'
    elif v < 1000000:
        s = f'{v / 1000:0.0f}k'
    elif v < 100000000:
        s = f'{v / 1000000:0.1f}M'
    elif v < 1000000000:
        s = f'{v / 1000000:0.0f}M'
    elif v < 100000000000:
        s = f'{v / 1000000000:0.1f}B'
    else:
        s = f'{v / 1000000000:0.1f}B'
    return sign + s


def human_readable_time_passed(seconds: Union[float, int], s=' с.', m=' мин.', h=' ч.', d=' дн.', exact=False):
    """
    Превращает чистые секунды в более удобную для восприятия форму.
    Это могут быть секунды, сколько-то минут, часов или даже дней.
    :param seconds:
    :param s:
    :param m:
    :param h:
    :param d:
    :param exact: стоит ли показывать время с высокой точностью. К примеру вместо "7 ч." показать "7 ч. 2 м. 11 с."
    :return:
    """
    seconds = round(seconds)
    if seconds < 60:
        return f'{seconds}{s}'

    minutes = int(seconds / 60)
    and_seconds = seconds - minutes * 60
    if minutes < 60:
        if exact:
            return f'{minutes}{m} {and_seconds}{s}'
        else:
            return f'{minutes}{m}'

    hours = int(minutes / 60)
    and_minutes = minutes - hours * 60
    if exact and hours < 24:
        return f'{hours}{h} {and_minutes}{m} {and_seconds}{s}'
    elif hours < 3:
        return f'{hours}{h} {and_minutes}{m}'
    elif hours < 24:
        return f'{hours}{h}'

    days = int(hours / 24)
    and_hours = hours - days * 24
    if exact:
        return f'{days}{d} {and_hours}{h} {and_minutes}{m} {and_seconds}{s}'
    elif days > 3 or and_hours == 0:
        return f'{days}{d}'
    else:
        return f'{days}{d} {and_hours}{h}'


def human_readable_bytes(b: int, zero="0", letters=("b", "k", "M", "G", "T", "E")):
    if b == 0:
        return zero
    power = int(math.log(b, 1024))
    if power > len(letters) - 1:
        return f"Очень много ({b})"
    v = b / math.pow(1024, power)
    sv = str(v)[:4].rstrip("0").rstrip(".")
    return sv + letters[power]


def human_readable_roubles(kop: int, dot=",", thousands=" ", positive_sign="") -> str:
    sign = "-" if kop < 0 else positive_sign
    kop = abs(kop)
    rubs: int = kop // 100
    kops: int = kop % 100
    return f"{sign}{rubs:,}".replace(",", thousands) + dot + f"{kops:02}"
