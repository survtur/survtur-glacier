import datetime
import os.path
import secrets
import sqlite3
import threading
from typing import Iterator, Union, TypedDict, Optional, List


class ArchiveInfo(TypedDict):
    archive_id: str
    parent: str
    name: str
    upload_timestamp: Union[None, float, int]
    modified_timestamp: Union[None, float, int]
    sha256: str
    size: Optional[int]
    is_dir: bool


class Inventory:

    def __init__(self, db_file: str):
        self._db_file: str = db_file
        exists = os.path.isfile(self.db_file)
        self._db = sqlite3.connect(self.db_file)
        with threading.Lock():
            if not exists:
                self._db.executescript("""
                    BEGIN TRANSACTION;
                    CREATE TABLE IF NOT EXISTS "meta" (
                        "name"	TEXT NOT NULL PRIMARY KEY,
                        "value"	TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS "archives" (
                        "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        "archive_id" TEXT NOT NULL UNIQUE,
                        "parent" TEXT NOT NULL,
                        "name" TEXT NOT NULL,
                        "name_search" TEXT NOT NULL,
                        "upload_timestamp" NUMERIC,
                        "modified_timestamp" NUMERIC,
                        "sha256" TEXT NOT NULL,
                        "size" INTEGER,
                        "is_dir" INTEGER NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS "is_dir_index" ON "archives" (
                        "is_dir" ASC
                    );
                    CREATE INDEX IF NOT EXISTS "SHA256TreeHash_index" ON "archives" (
                        "sha256" ASC
                    );
                    CREATE INDEX IF NOT EXISTS "parent_index" ON "archives" (
                        "parent" ASC
                    );
                    CREATE INDEX IF NOT EXISTS "name_index" ON "archives" (
                        "name" ASC
                    );
                  
                    COMMIT;
                    """)
        self._db.row_factory = sqlite3.Row
        self._fix_non_existing_parents()

    @property
    def db_file(self) -> str:
        return self._db_file

    def put_archive(self, a: ArchiveInfo):
        self._put_archive(a)
        self._fix_non_existing_parents()

    def _put_archive(self, a: ArchiveInfo):
        self._db.execute("""
                            INSERT INTO archives
                                (archive_id, parent, name, upload_timestamp, modified_timestamp,
                                 sha256, size, is_dir, name_search)
                                VALUES
                                (:aid,     :p,     :n,   :u,          :t,             :sha,  :s,     :i, :ns)""",
                         {
                             "aid": a['archive_id'],
                             "p": a['parent'],
                             "n": a['name'],
                             "u": a['upload_timestamp'],
                             "t": a['modified_timestamp'],
                             "sha": a['sha256'],
                             "s": a['size'],
                             "i": int(a['is_dir']),
                             "ns": a['name'].upper()
                         })

    def save(self):
        self._db.commit()

    def close(self):
        self._db.close()

    @property
    def inventory_date(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.inventory_timestamp)

    @property
    def inventory_timestamp(self) -> float:
        cur = self._db.execute("SELECT value FROM meta WHERE name='InventoryDate'")
        return float(cur.fetchone()[0])

    @property
    def size(self) -> int:
        cur = self._db.execute('SELECT SUM(Size) FROM archives')
        return cur.fetchone()[0]

    @property
    def vault_name(self) -> str:
        cur = self._db.execute("SELECT value FROM meta WHERE name='VaultName'")
        return cur.fetchone()[0]

    @property
    def vault_arn(self) -> str:
        cur = self._db.execute("SELECT value FROM meta WHERE name='VaultARN'")
        return cur.fetchone()[0]

    def set_vault_info(self, vault_arn: str, timestamp: Union[int, float]):
        name = vault_arn.split("/")[-1]
        self._db.execute("""INSERT INTO meta (name, value) VALUES ('VaultARN', :arn)
                            ON CONFLICT (name) DO
                            UPDATE SET value=:arn""", {'arn': vault_arn})
        self._db.execute("""INSERT INTO meta (name, value) VALUES ('VaultName', :name)
                            ON CONFLICT (name) DO
                            UPDATE SET value=:name""", {'name': name})
        self._db.execute("""INSERT INTO meta (name, value) VALUES ('InventoryDate', :ts)
                            ON CONFLICT (name) DO
                            UPDATE SET value=:ts""", {'ts': str(timestamp)})

    def find_archives(self, like: str, escape: str = "\\",
                      sort_by: str = "name", asc: bool = True) -> Iterator[ArchiveInfo]:
        assert self._is_column_exists(sort_by)
        order = "ASC" if asc else "DESC"
        upper = like.upper()
        # noinspection SqlResolve
        cur = self._db.execute(f"SELECT * FROM archives WHERE name_search LIKE ? ESCAPE ?" +
                               f"ORDER BY is_dir DESC, name, `{sort_by}` {order}",
                               (upper, escape))
        for row in cur:
            yield dict(row)

    def get_path_content(self, parent: str, sort_by: str = "name", asc: bool = True) -> Iterator[ArchiveInfo]:
        assert self._is_column_exists(sort_by)
        order = "ASC" if asc else "DESC"
        # noinspection SqlResolve
        cur = self._db.execute(f"SELECT * FROM archives WHERE parent=? ORDER BY is_dir DESC, `{sort_by}` {order}",
                               (parent,))
        for row in cur:
            yield dict(row)

    def clear(self):
        self._db.execute("DELETE FROM archives WHERE 1")

    def archives_count(self) -> int:
        cur = self._db.execute("SELECT COUNT(*) FROM archives WHERE is_dir=0")
        return cur.fetchone()[0]

    def find(self, *, size: Optional[int] = None, sha256_tree_hash: Optional[str] = None) -> Iterator[ArchiveInfo]:
        where = [" is_dir=0 "]

        if size is not None:
            where.append(" size=:size ")
        if sha256_tree_hash is not None:
            where.append(" sha256=:sha256 ")

        where_str = " AND ".join(where)

        query = f"SELECT * FROM archives WHERE {where_str}"
        cur = self._db.execute(query, {"size": size, "sha256": sha256_tree_hash})
        for row in cur:
            yield dict(row)

    def _is_column_exists(self, name: str) -> bool:
        # noinspection SqlResolve
        cur = self._db.execute("SELECT COUNT(*) FROM pragma_table_info('archives') where name=?", (name,))
        return bool(cur.fetchone()[0])

    def _fix_non_existing_parents(self):
        cur = self._db.execute("SELECT DISTINCT(parent) FROM archives WHERE parent!=''")
        parents_to_check: List[str] = [row[0] for row in cur]
        while parents_to_check:
            p = parents_to_check.pop()
            assert p.endswith("/")
            p = p[:-1]
            path_parts = p.split("/")
            *its_parent, its_name = path_parts
            its_name += "/"
            its_parent = "/".join(its_parent)
            if its_parent:
                its_parent += "/"

            cur2 = self._db.execute("SELECT COUNT(*) FROM archives WHERE name=? AND parent=?", (its_name, its_parent))
            found = cur2.fetchone()[0]
            if found:
                continue

            urlsafe = secrets.token_urlsafe()
            virtual_dir = ArchiveInfo(
                archive_id="VIRTUAL_DIR " + urlsafe,
                parent=its_parent,
                name=its_name,
                upload_timestamp=0,
                modified_timestamp=0,
                sha256="VIRTUAL_DIR " + urlsafe,
                size=None,
                is_dir=True
            )
            self._put_archive(virtual_dir)
            if its_parent != "":
                parents_to_check.append(its_parent)
