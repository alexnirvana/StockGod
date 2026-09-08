"""Consistent SQLite backup and non-destructive restore. Stop services before switching restored files."""
import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def backup(source: Path, destination: Path):
    if not source.is_file():
        raise ValueError(f"Source database does not exist: {source}")
    if destination.exists():
        raise ValueError("Destination exists. Choose a new filename to preserve existing data.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
        result = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise ValueError(f"Integrity check failed: {result}")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--source", type=Path, default=ROOT / "data" / "stockgod.db")
    args = parser.parse_args()
    print(backup(args.source.resolve(), args.destination.resolve()))

