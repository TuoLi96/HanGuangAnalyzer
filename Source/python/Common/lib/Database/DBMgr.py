from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any
import threading

SqlParams = Sequence[Any] | Mapping[str, Any]

class DBMgr:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(
            self.path,
            timeout=5.0,
            isolation_level=None,
            check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row
        self._configure()

    def _configure(self) -> None:
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.execute("PRAGMA foreign_keys=ON")

    def execute(self, sql: str, params: SqlParams = ()) -> sqlite3.Cursor:
        with self.lock:
            return self.connection.execute(sql, params)

    def execute_script(self, script: str) -> None:
        with self.lock:
            self.connection.executescript(script)

    def execute_many(
        self,
        sql: str,
        rows: Iterable[SqlParams],
    ) -> sqlite3.Cursor:
        with self.lock:
            return self.connection.executemany(sql, rows)

    def query(self, sql: str, params: SqlParams = ()) -> list[dict[str, Any]]:
        with self.lock:
            cursor = self.connection.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self.lock:
            self.connection.execute("BEGIN")
            try:
                yield
            except BaseException:
                self.connection.execute("ROLLBACK")
                raise
            else:
                self.connection.execute("COMMIT")

    def execute_batch(self, statements: Iterable[str]) -> None:
        with self.transaction():
            for statement in statements:
                self.connection.execute(statement)

    def close(self) -> None:
        with self.lock:
            self.connection.close()

    def __enter__(self) -> "DBMgr":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
