#!/usr/bin/env python3
"""Import the books identified in Espen's 14 physical-shelf photographs.

The manifest is intentionally conservative. Existing works are linked by an
explicit canonical title; new records remain unread/unknown. Running the
script repeatedly is idempotent.
"""
import argparse
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from library import DATA, ROOT, all_books, connect, key, new_book, norm, now, save, snapshot

MANIFEST = ROOT / "physical_shelf_manifest.json"
REPORT_DIR = DATA / "imports"


def load_manifest():
    rows = json.loads(MANIFEST.read_text())
    return [r for r in rows if not r.get("skip")]


def formats_for(book):
    formats = set(book.get("formats") or [])
    # Older records stored only the single medium field.
    if book.get("medium") in {"paper", "ebook", "audio"}:
        formats.add(book["medium"])
    return formats


def add_paper(book):
    formats = formats_for(book)
    formats.add("paper")
    book["formats"] = sorted(formats)
    book["medium"] = next(iter(formats)) if len(formats) == 1 else "mixed"


def find_existing(books, row):
    wanted = row.get("match_title")
    if wanted:
        matches = [b for b in books if norm(b["title"]) == norm(wanted)]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one canonical match for {wanted!r}, found {len(matches)}")
        return matches[0]
    exact = [b for b in books if key(b["title"], b["author"]) == key(row["title"], row["author"])]
    return exact[0] if len(exact) == 1 else None


def import_manifest(dry_run=False):
    c = connect()
    before = {b["id"]: b for b in all_books(c)}
    working = list(before.values())
    added, linked, unchanged = [], [], []

    for row in load_manifest():
        book = find_existing(working, row)
        is_new = book is None
        if is_new:
            book = new_book(row["title"], row["author"])
            book["medium"] = "paper"
            book["formats"] = ["paper"]
            book["source"] = "Fysisk bokhylle"
            book["series"] = row.get("series", "")
            book["series_index"] = row.get("series_index")
            book["title_uncertain"] = bool(row.get("title_uncertain", False))
            working.append(book)
            added.append(book["title"])
        else:
            old_formats = set(formats_for(book))
            add_paper(book)
            (linked if "paper" not in old_formats else unchanged).append(book["title"])

        provenance = "Fysisk bokhylle · fotografert 2026-09-25"
        if provenance not in book.get("provenance", []):
            book.setdefault("provenance", []).append(provenance)
        photos = set(book.get("physical_photo_sources", []))
        photos.add(row["photo"])
        book["physical_photo_sources"] = sorted(photos)
        book["physical_owned"] = True
        book["physical_copies"] = max(int(book.get("physical_copies", 1)), int(row.get("physical_copies", 1)))
        if row.get("notes"):
            note = row["notes"]
            if note not in book.get("notes", ""):
                book["notes"] = (book.get("notes", "") + ("\n" if book.get("notes") else "") + note)
        add_paper(book)
        if not dry_run:
            save(c, book, event=True)

    # The import must never modify reading facts on pre-existing records.
    protected = ["status", "year", "year_uncertain", "finished_date", "progress", "progress_unit", "read_count"]
    for book_id, old in before.items():
        new = next(b for b in working if b["id"] == book_id)
        for field in protected:
            if new.get(field) != old.get(field):
                raise RuntimeError(f"Reading field {field} changed for {old['title']}")

    result = {
        "at": now(),
        "manifest_rows": len(load_manifest()),
        "added_count": len(added),
        "linked_count": len(linked),
        "already_physical_count": len(unchanged),
        "added": added,
        "linked": linked,
        "dry_run": dry_run,
    }
    if dry_run:
        c.rollback()
    else:
        snapshot(c)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (REPORT_DIR / f"physical-shelf-{stamp}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    c.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(import_manifest(args.dry_run), ensure_ascii=False, indent=2))
