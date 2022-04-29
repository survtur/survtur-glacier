import configparser
import os.path
import shutil
from typing import Optional

from ..common.helpers import is_power_of_two


class Config:

    def __init__(self, path: str):
        if os.path.isdir(path):
            self._config_file = os.path.join(path, 'config.ini')
        elif os.path.isfile(path):
            self._config_file = path

        if not os.path.isfile(self._config_file):
            src = os.path.join(os.path.dirname(__file__), "default_config.ini")
            shutil.copy(src, self._config_file)

        self._config = configparser.ConfigParser()
        self._config.read(self._config_file)

        self._workdir: str = os.path.dirname(self._config_file)
        self._inventories_dir: str = os.path.join(self._workdir, 'inventories')
        if not os.path.isdir(self._inventories_dir):
            os.mkdir(self._inventories_dir)

    def get_config_file_locations(self) -> str:
        return self._config_file

    @property
    def client_id(self) -> str:
        return self._config['LOCAL']['client_id']

    @client_id.setter
    def client_id(self, s: str):
        assert s.isalnum()
        self._config['LOCAL']['client_id'] = s

    @property
    def task_threads(self) -> int:
        return int(self._config['LOCAL']['task_threads'])

    @task_threads.setter
    def task_threads(self, n: int):
        assert n > 0
        self._config['LOCAL']['task_threads'] = str(n)

    @property
    def fast_glacier_style_naming(self) -> bool:
        return bool(int(self._config['LOCAL']['fast_glacier_style_naming']) != 0)

    @fast_glacier_style_naming.setter
    def fast_glacier_style_naming(self, b: bool):
        self._config['LOCAL']['fast_glacier_style_naming'] = "1" if b else "0"

    @property
    def workdir(self) -> str:
        return self._workdir

    @property
    def access_key_id(self) -> str:
        return self._config['AWS']['access_key_id']

    @property
    def secret_access_key(self) -> str:
        return self._config['AWS']['secret_access_key']

    @property
    def region_name(self) -> str:
        return self._config['AWS']['region_name']

    def get_inventories_location(self, and_file: Optional[str] = None) -> str:
        """
        Returns directory with inventories.
        If `and_file` specified, then returns this file from inventories directory.
        """
        if and_file is None:
            return self._inventories_dir
        else:
            return os.path.join(self._inventories_dir, and_file)

    @property
    def chunk_size_mb(self) -> int:
        return int(self._config['LOCAL']['chunk_size_mb'])

    @chunk_size_mb.setter
    def chunk_size_mb(self, i: int):
        assert i > 0, i
        assert is_power_of_two(i), i
        self._config['LOCAL']['chunk_size_mb'] = str(i)

    @property
    def fast_glacier_style_dirs(self) -> bool:
        return bool(int(self._config['LOCAL']['fast_glacier_style_dirs']) != 0)

    @fast_glacier_style_dirs.setter
    def fast_glacier_style_dirs(self, b: bool):
        self._config['LOCAL']['fast_glacier_style_dirs'] = "1" if b else "0"

    @property
    def restricted_naming(self) -> bool:
        return bool(int(self._config['LOCAL']['restricted_naming']) != 0)

    @restricted_naming.setter
    def restricted_naming(self, b: bool):
        self._config['LOCAL']['restricted_naming'] = "1" if b else "0"
