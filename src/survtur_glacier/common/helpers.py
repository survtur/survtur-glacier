import threading
from datetime import datetime, timezone

KB = 1024
MB = KB * 1024
GB = MB * 1024


def date_string_to_date(cd: str) -> datetime:
    cd = cd.replace("UTC", "Z")
    if '.' in cd:
        return datetime.strptime(cd, "%Y-%m-%dT%H:%M:%S.%fZ")
    else:
        return datetime.strptime(cd, "%Y-%m-%dT%H:%M:%SZ")


def date_to_date_string(d: datetime) -> str:
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def empty_callable(*_, **__):
    pass


def is_power_of_two(n: int) -> bool:
    return (n & (n - 1) == 0) and n != 0


def locked_print(*a, **k):
    with threading.Lock():
        print(*a, **k)
