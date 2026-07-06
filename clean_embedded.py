#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embedded project archive cleaner for Keil MDK / STM32CubeMX projects.

Use this when a project is finalized and you want to archive it without bulky,
regenerable build artifacts. The default mode is a dry run. Add --yes to delete.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import os
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass


# Files that must never be removed by this tool.
PROTECTED_FILE_PATTERNS = {
    # Source and headers
    "*.c", "*.h", "*.s", "*.asm", "*.cpp", "*.hpp", "*.cxx", "*.inc",
    # STM32CubeMX / Eclipse / Keil project metadata
    "*.ioc", ".mxproject", "*.mxproject", ".project", ".cproject",
    "*.uvproj", "*.uvprojx", "*.uvopt", "*.uvoptx", "*.uvgui.*", "*.uvguix.*",
    # Linker/debug/project support files
    "*.sct", "*.scf", "*.ld", "*.ini", "*.scvd", "*.pdsc",
    # Firmware and useful release outputs
    "*.hex", "*.bin", "*.map",
    # Human/project assets
    "*.md", "*.txt", "*.pdf", "*.doc", "*.docx", "*.xls", "*.xlsx",
    "*.ppt", "*.pptx", "*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif", "*.svg",
    "*.json", "*.xml", "*.yaml", "*.yml",
    "*.zip", "*.rar", "*.7z", "*.tar", "*.gz",
}

# Build products that are safe to regenerate.
DELETE_FILE_PATTERNS = {
    "*.o", "*.obj", "*.d", "*.dep", "*.lst", "*.crf", "*.lnp", "*.plg",
    "*.htm", "*.html", "*.axf", "*.elf", "*.build_log.htm",
    "*.__i", "*.i", "*.ii", "*.su",
    "*.pyc", "*.pyo", "*.swp", "*.swo", "*~",
    "JLinkLog.txt", "*.jlink", "*.log",
}

BACKUP_FILE_PATTERNS = {"*.bak", "*.orig", "*.old"}

# Directories that are always generated build output.
DELETE_DIR_NAMES = {"Objects", "Listings", "__pycache__"}

# Directory names that are often generated build output, but may also be user folders.
CONDITIONAL_DELETE_DIR_NAMES = {"Debug", "Release"}

# Directories to leave untouched and not traverse.
SKIP_DIR_NAMES = {
    ".git", ".svn", ".hg", ".vscode",
    "RTE", "DebugConfig", ".settings",
}

BUILD_DIR_MARKERS = {
    "makefile", "objects.mk", "sources.mk", "subdir.mk", "*.o", "*.obj", "*.axf", "*.elf",
}

ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "cyan": "\033[96m",
}


@dataclass(frozen=True)
class Entry:
    path: Path
    size: int
    reason: str


def supports_color(no_color: bool) -> bool:
    if no_color or not sys.stdout.isatty():
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            return True
    except Exception:
        pass
    return True


class Printer:
    def __init__(self, use_color: bool) -> None:
        self.use_color = use_color

    def c(self, text: str, *styles: str) -> str:
        if not self.use_color:
            return text
        return "".join(ANSI[s] for s in styles) + text + ANSI["reset"]

    def title(self, text: str) -> None:
        print(self.c(text, "bold", "cyan"))
        print(self.c("-" * len(text), "cyan"))

    def kv(self, key: str, value: str) -> None:
        print(f"  {self.c(key + ':', 'bold'):<18} {value}")


def _matches(name: str, patterns: Iterable[str]) -> bool:
    lower = name.lower()
    return any(fnmatch.fnmatch(lower, pat.lower()) for pat in patterns)


def _is_protected_file(path: Path) -> bool:
    return _matches(path.name, PROTECTED_FILE_PATTERNS)


def _dir_size(path: Path) -> int:
    total = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not (Path(root) / d).is_symlink()]
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def _dir_contains_protected_files(path: Path) -> bool:
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not (Path(root) / d).is_symlink()]
        if any(_matches(name, PROTECTED_FILE_PATTERNS) for name in files):
            return True
    return False


def _looks_like_build_dir(path: Path) -> bool:
    try:
        names = [p.name for p in path.iterdir()]
    except OSError:
        return False
    return any(_matches(name, BUILD_DIR_MARKERS) for name in names)


def scan(root: Path, include_logs: bool = True, include_backups: bool = False) -> tuple[list[Entry], list[Entry]]:
    files: list[Entry] = []
    dirs: list[Entry] = []

    file_patterns = set(DELETE_FILE_PATTERNS)
    if include_backups:
        file_patterns.update(BACKUP_FILE_PATTERNS)
    if not include_logs:
        file_patterns.discard("*.log")
        file_patterns.discard("JLinkLog.txt")

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        current = Path(dirpath)
        kept: list[str] = []

        for dirname in dirnames:
            full = current / dirname
            if dirname in SKIP_DIR_NAMES or full.is_symlink():
                continue

            if dirname in DELETE_DIR_NAMES:
                if _dir_contains_protected_files(full):
                    kept.append(dirname)
                else:
                    dirs.append(Entry(full, _dir_size(full), "generated directory"))
                continue

            if dirname in CONDITIONAL_DELETE_DIR_NAMES and _looks_like_build_dir(full):
                if _dir_contains_protected_files(full):
                    kept.append(dirname)
                else:
                    dirs.append(Entry(full, _dir_size(full), "build directory"))
                continue

            kept.append(dirname)

        dirnames[:] = kept

        for filename in filenames:
            full = current / filename
            if full.is_symlink() or _is_protected_file(full):
                continue
            if _matches(filename, file_patterns):
                files.append(Entry(full, _file_size(full), "generated file"))

    return files, dirs


def format_size(value: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def folder_key(path: Path, root: Path) -> str:
    value = rel(path, root)
    parts = Path(value).parts
    return str(Path(*parts[:2])) if len(parts) > 1 else str(Path(parts[0]))


def print_summary(printer: Printer, root: Path, files: list[Entry], dirs: list[Entry], limit: int, details: bool) -> None:
    total = sum(e.size for e in files) + sum(e.size for e in dirs)
    printer.kv("Matched", f"{len(files)} files, {len(dirs)} directories")
    printer.kv("Space", format_size(total))

    if not files and not dirs:
        print()
        print(printer.c("Nothing to clean.", "green", "bold"))
        return

    by_ext = Counter((e.path.suffix.lower() or "[no ext]") for e in files)
    by_folder = Counter()
    for entry in files + dirs:
        by_folder[folder_key(entry.path, root)] += entry.size

    print()
    print(printer.c("Top folders", "bold"))
    for folder, size in by_folder.most_common(8):
        print(f"  {folder:<42} {format_size(size):>10}")

    if by_ext:
        print()
        print(printer.c("File types", "bold"))
        ext_line = "  " + "  ".join(f"{ext}:{count}" for ext, count in by_ext.most_common(10))
        print(ext_line)

    entries = [*files, *dirs]
    if details or limit > 0:
        print()
        title = "Details" if details else f"Preview first {min(limit, len(entries))}"
        print(printer.c(title, "bold"))
        shown = entries if details else entries[:limit]
        for entry in shown:
            kind = "DIR " if entry in dirs else "FILE"
            print(f"  {kind} {rel(entry.path, root)} ({format_size(entry.size)})")
        hidden = len(entries) - len(shown)
        if hidden > 0:
            print(printer.c(f"  ... {hidden} more item(s), use --details to list everything.", "dim"))


def write_log(log_path: Path, root: Path, files: list[Entry], dirs: list[Entry], dry_run: bool) -> None:
    total = sum(e.size for e in files) + sum(e.size for e in dirs)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        f.write("Embedded project cleanup log\n")
        f.write("=" * 60 + "\n")
        f.write(f"Time: {_dt.datetime.now():%Y-%m-%d %H:%M:%S}\n")
        f.write(f"Root: {root}\n")
        f.write(f"Mode: {'dry-run' if dry_run else 'delete'}\n")
        f.write(f"Items: {len(files)} files, {len(dirs)} directories, {format_size(total)}\n\n")
        for entry in files:
            f.write(f"FILE {rel(entry.path, root)} ({format_size(entry.size)})\n")
        for entry in dirs:
            f.write(f"DIR  {rel(entry.path, root)} ({format_size(entry.size)})\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely clean regenerable Keil/STM32CubeMX build artifacts before archiving."
    )
    parser.add_argument("-r", "--root", required=True, help="Project root to scan")
    parser.add_argument("--yes", action="store_true", help="Actually delete matched files/directories")
    parser.add_argument("--details", action="store_true", help="Print every matched item")
    parser.add_argument("--limit", type=int, default=20, help="Preview item count when --details is not used")
    parser.add_argument("--keep-logs", action="store_true", help="Keep *.log and JLinkLog.txt")
    parser.add_argument("--include-backups", action="store_true", help="Also delete *.bak, *.orig and *.old")
    parser.add_argument("--no-color", action="store_true", help="Disable colored terminal output")
    parser.add_argument("--log", help="Write cleanup report to this file")
    parser.add_argument("--exclude", action="append", default=[], help="Exclude path pattern, can be repeated")
    args = parser.parse_args()

    printer = Printer(supports_color(args.no_color))
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: directory does not exist: {root}", file=sys.stderr)
        return 2

    log_path = Path(args.log).expanduser().resolve() if args.log else None
    files, dirs = scan(root, include_logs=not args.keep_logs, include_backups=args.include_backups)

    if log_path:
        files = [e for e in files if e.path.resolve() != log_path]
        dirs = [e for e in dirs if not _is_under(log_path, e.path)]

    if args.exclude:
        def excluded(entry: Entry) -> bool:
            value = str(entry.path)
            value_rel = rel(entry.path, root)
            return any(fnmatch.fnmatch(value, pat) or fnmatch.fnmatch(value_rel, pat) for pat in args.exclude)
        files = [e for e in files if not excluded(e)]
        dirs = [e for e in dirs if not excluded(e)]

    files.sort(key=lambda e: str(e.path).lower())
    dirs.sort(key=lambda e: str(e.path).lower())

    mode = "DELETE MODE" if args.yes else "DRY RUN"
    printer.title("Keil / STM32CubeMX Archive Cleaner")
    printer.kv("Mode", printer.c(mode, "red" if args.yes else "yellow", "bold"))
    printer.kv("Root", str(root))
    print_summary(printer, root, files, dirs, max(0, args.limit), args.details)

    if log_path:
        write_log(log_path, root, files, dirs, dry_run=not args.yes)
        print()
        printer.kv("Log", str(log_path))

    if not args.yes:
        print()
        print(printer.c("Dry run only. Add --yes after checking the list to delete matched items.", "yellow"))
        return 0

    errors: list[tuple[Path, str]] = []
    for entry in files:
        if not _is_under(entry.path, root):
            errors.append((entry.path, "outside root"))
            continue
        try:
            entry.path.unlink()
        except OSError as exc:
            errors.append((entry.path, str(exc)))

    for entry in sorted(dirs, key=lambda e: len(e.path.parts), reverse=True):
        if not _is_under(entry.path, root):
            errors.append((entry.path, "outside root"))
            continue
        try:
            shutil.rmtree(entry.path)
        except OSError as exc:
            errors.append((entry.path, str(exc)))

    print()
    if errors:
        print(printer.c("Cleanup finished with errors:", "red", "bold"), file=sys.stderr)
        for path, message in errors:
            print(f"  {path}: {message}", file=sys.stderr)
        return 1

    print(printer.c("Cleanup finished.", "green", "bold"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())