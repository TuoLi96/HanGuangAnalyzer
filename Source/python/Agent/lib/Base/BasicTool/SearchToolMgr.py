import os
import fnmatch
from typing import Optional
import json
from tqdm import tqdm
import json
import shutil
import subprocess
from pathlib import Path

from HG.Common.Path import PathMgr

class SearchToolMgr():
    def __init__(self):
        super().__init__()
        self.path_mgr = PathMgr()

        self.search_extensions = {".c", ".h", ".rst", ".txt", ".md"}
        self.search_root = self.path_mgr.get_checked_root()
        self._file_cache = None
        self.batch_size = 500

    def refresh_file_cache(self):
        rg = shutil.which("rg")
        if rg is None:
            return "ripgrep (rg) is not installed or not in PATH"

        cmd = [rg, "--files", "--color", "never", str(self.search_root)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, check=False)
        except subprocess.TimeoutExpired:
            return "file listing timed out"
        except OSError as exc:
            return f"failed to list files: {exc}"

        if result.returncode not in (0, 1):
            return f"file listing failed: {result.stderr.strip()}"

        extensions = {
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in self.search_extensions
        }

        self._file_cache = [
            Path(filename).relative_to(self.search_root).as_posix()
            for filename in result.stdout.splitlines()
            if Path(filename).suffix.lower() in extensions
        ]

        return len(self._file_cache)

    def get_candidate_files(self, path, file_pattern="*"):
        if self._file_cache is None:
            count = self.refresh_file_cache()
            if isinstance(count, str):
                return count

        relative_root = Path(path)

        if relative_root.is_absolute() or ".." in relative_root.parts:
            return "path must be relative to the search root"

        pattern = file_pattern.replace("\\", "/")
        if pattern.startswith("/") or ".." in pattern.split("/"):
            return "file_pattern must be a relative path pattern"

        results = []

        for relative_file in self._file_cache:
            file_path = Path(relative_file)

            try:
                scoped_file = file_path.relative_to(relative_root)
            except ValueError:
                continue

            if "/" in pattern:
                matched = fnmatch.fnmatchcase(scoped_file.as_posix(), pattern)
            else:
                matched = fnmatch.fnmatchcase(scoped_file.name, pattern)
            if matched:
                results.append(str(self.search_root / file_path))

        return results

    def search_text(self, query: str, path: str = "", file_pattern: str = "*", case_sensitive: bool = True):
        if not query:
            return "query must not be empty"

        files = self.get_candidate_files(path=path, file_pattern=file_pattern)

        if isinstance(files, str):
            return files
        if not files:
            return []

        rg = shutil.which("rg")
        if rg is None:
            return "ripgrep (rg) is not installed or not in PATH"

        results = []

        for start in range(0, len(files), self.batch_size):
            batch = files[start:start + self.batch_size]
            cmd = [rg, "--json", "--fixed-strings"]
            if not case_sensitive:
                cmd.append("--ignore-case")
            cmd.extend(["--", query, *batch])
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return "search timed out"
            except OSError as exc:
                return f"search failed: {exc}"
            if result.returncode == 1:
                continue
            if result.returncode != 0:
                return f"search failed: {result.stderr.strip()}"
            for output_line in result.stdout.splitlines():
                try:
                    item = json.loads(output_line)
                except json.JSONDecodeError:
                    continue
                if item.get("type") != "match":
                    continue
                data = item["data"]
                raw_path = data["path"].get("text")
                line_number = data.get("line_number")
                content = data["lines"].get("text")
                if raw_path is None or content is None:
                    continue
                try:
                    relative_path = Path(raw_path).relative_to(self.search_root).as_posix()
                except ValueError:
                    continue
                results.append((relative_path, line_number, content.rstrip("\r\n")))

        return results

    def read_file(self, path: str, start_line: int = 1, end_line: Optional[int] = None) -> str:
        abs_path = Path(self.path_mgr.get_abspath_from_src(path))

        if not abs_path.exists():
            return f"{path} not exists"
        if not abs_path.is_file():
            return f"{path} is not a regular file"
        if start_line < 1:
            return "start_line must be >= 1"
        if end_line is not None and end_line < start_line:
            return "end_line must be >= start_line"
        output = []
        try:
            with abs_path.open("r", encoding="utf-8", errors="replace") as f:
                for line_number, line in enumerate(f, start=1):
                    if line_number < start_line:
                        continue
                    if end_line is not None and line_number > end_line:
                        break
                    output.append(f"{line_number:6d} | {line.rstrip()}")
        except OSError as exc:
            return f"failed to read file: {exc}"

        return "\n".join(output)
