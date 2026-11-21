"""Make a consistent SQLite copy for backup, or restore into a NEW file."""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3


def copy_database(source, destination):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as origin:
        with destination.open('xb'):
            pass
        try:
            with closing(sqlite3.connect(destination)) as target:
                origin.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or target.execute('PRAGMA foreign_key_check').fetchone():
                    raise ValueError('Database integrity check failed')
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('destination', help='A new SQLite file')
    args = parser.parse_args()
    print(copy_database(args.source, args.destination))
