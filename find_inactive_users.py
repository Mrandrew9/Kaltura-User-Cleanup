#!/usr/bin/env python3
"""Build a Kaltura bulk-deletion CSV by comparing a Kaltura user export
against an HR/IdP active-user export (AD, Workday, ADP, Okta...).

Usage:
    python find_inactive_users.py active_users.csv kaltura_users.csv \
        --active-col email --kaltura-col "User ID" \
        --exclude admins_and_service_accounts.txt --batch-size 100

Writes bulk-user-deactivation-001.csv, -002.csv, ... (one file per batch),
each in Kaltura's bulk format: a "*action,userID" header, then "3,<userID>"
rows (action 3 = delete). Review the output with HR before uploading.
"""

import argparse
import csv
import sys
from pathlib import Path


def read_ids(path: Path, column: str) -> set[str]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if column not in (reader.fieldnames or []):
            sys.exit(f"{path}: column '{column}' not found. Columns: {reader.fieldnames}")
        return {row[column].strip().lower() for row in reader if row[column].strip()}


def read_exclusions(path: Path | None) -> set[str]:
    if not path:
        return set()
    lines = path.read_text(encoding="utf-8").splitlines()
    return {line.strip().lower() for line in lines if line.strip() and not line.startswith("#")}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("active_csv", type=Path, help="Export of currently active employees")
    p.add_argument("kaltura_csv", type=Path, help="User export from KMC")
    p.add_argument("--active-col", default="email", help="Email/ID column in the active export")
    p.add_argument("--kaltura-col", default="User ID", help="User ID column in the Kaltura export")
    p.add_argument("--exclude", type=Path, help="File of user IDs to never delete (admins, service accounts)")
    p.add_argument("--batch-size", type=int, default=100, help="Users per upload file (Kaltura recommends 100)")
    p.add_argument("--out-prefix", default="bulk-user-deactivation")
    args = p.parse_args()

    active = read_ids(args.active_csv, args.active_col)
    kaltura = read_ids(args.kaltura_csv, args.kaltura_col)
    protected = read_exclusions(args.exclude)
    to_delete = sorted(kaltura - active - protected)

    print(f"Active employees: {len(active)}")
    print(f"Kaltura users:    {len(kaltura)}")
    print(f"Protected:        {len(kaltura & protected)}")
    print(f"To delete:        {len(to_delete)}")

    for i in range(0, len(to_delete), args.batch_size):
        out = Path(f"{args.out_prefix}-{i // args.batch_size + 1:03d}.csv")
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["*action", "userID"])
            w.writerows([3, uid] for uid in to_delete[i : i + args.batch_size])
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
