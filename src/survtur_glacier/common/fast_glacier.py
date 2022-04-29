import base64
import re
from datetime import datetime
from typing import NamedTuple


class FastGlacierArchiveInfo(NamedTuple):
    parent: str
    name: str
    is_dir: bool
    last_modified: datetime


def from_fast_glacier(s: str) -> FastGlacierArchiveInfo:
    r = re.compile(r"^<m><v>(?P<v>.*)</v><p>(?P<p>.*)</p><lm>(?P<lm>.*)</lm></m>$")
    match = r.match(s)
    assert match.group('v') == '4'
    name = base64.b64decode(match.group('p')).decode('utf8')
    dt = datetime.strptime(match.group('lm'), "%Y%m%dT%H%M%SZ")

    is_dir = name.endswith("/")
    parts = name.split("/")
    name = (parts[-2] + "/") if is_dir else parts[-1]
    parent = "/".join(parts[:-2] if is_dir else parts[:-1])
    if parent:
        parent += "/"

    return FastGlacierArchiveInfo(parent=parent, name=name, is_dir=is_dir, last_modified=dt)


def to_fast_glacier(f: FastGlacierArchiveInfo) -> str:
    path = f.parent + f.name
    p = base64.b64encode(path.encode('utf8')).decode('ascii')
    lm = f.last_modified.strftime("%Y%m%dT%H%M%SZ")
    return f"<m><v>4</v><p>{p}</p><lm>{lm}</lm></m>"
