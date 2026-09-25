#!/usr/bin/env python3
"""Best-effort digital cover matching for photographed physical books.

Uses public Google Books metadata. A cover is accepted only when title and
author similarity clear a conservative threshold. Existing covers are never
overwritten. The report keeps rejected candidates reviewable.
"""
import json
import ssl
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path

from PIL import Image

from library import DATA, ROOT, all_books, connect, norm, now, save, snapshot

REPORT_DIR = DATA / "imports"
COVER_DIR = ROOT / "static" / "covers"
PROVENANCE = "Fysisk bokhylle · fotografert 2026-09-25"
UA = "Bokhylla-local/1.0"


def similarity(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def author_similarity(wanted, candidates):
    joined = ", ".join(candidates or [])
    return max(similarity(wanted, joined), max((similarity(part, joined) for part in wanted.split(",")), default=0))


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as response:
        return json.load(response)


def google_candidates(book):
    query = f'intitle:"{book["title"]}" inauthor:"{book["author"]}"'
    url = "https://www.googleapis.com/books/v1/volumes?" + urllib.parse.urlencode({"q": query, "maxResults": 10, "printType": "books"})
    payload = get_json(url)
    choices = []
    for item in payload.get("items", []):
        info = item.get("volumeInfo", {})
        images = info.get("imageLinks", {})
        image = images.get("extraLarge") or images.get("large") or images.get("medium") or images.get("thumbnail")
        if not image:
            continue
        title_score = similarity(book["title"], info.get("title", ""))
        author_score = author_similarity(book["author"], info.get("authors", []))
        score = title_score * 0.8 + author_score * 0.2
        choices.append({
            "score": round(score, 4),
            "title_score": round(title_score, 4),
            "author_score": round(author_score, 4),
            "title": info.get("title", ""),
            "authors": info.get("authors", []),
            "image": image.replace("http://", "https://"),
            "google_books_id": item.get("id", ""),
            "isbn": next((x.get("identifier") for x in info.get("industryIdentifiers", []) if x.get("type") in {"ISBN_13", "ISBN_10"}), ""),
        })
    return sorted(choices, key=lambda x: x["score"], reverse=True)


def acceptable(choice):
    return choice and choice["title_score"] >= 0.76 and (choice["author_score"] >= 0.30 or choice["title_score"] >= 0.96)


def save_image(url, target):
    # Request a useful resolution when Google supplies a zoom parameter.
    parsed = urllib.parse.urlsplit(url)
    params = dict(urllib.parse.parse_qsl(parsed.query))
    params["zoom"] = "2"
    url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(params), parsed.fragment))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as response:
        raw = response.read(12 * 1024 * 1024)
    image = Image.open(BytesIO(raw)).convert("RGB")
    if image.width < 80 or image.height < 120:
        raise ValueError(f"image too small: {image.width}x{image.height}")
    image.thumbnail((1000, 1600), Image.Resampling.LANCZOS)
    image.save(target, "JPEG", quality=90, optimize=True)
    return {"width": image.width, "height": image.height}


def run():
    c = connect()
    books = [b for b in all_books(c) if PROVENANCE in b.get("provenance", []) and not b.get("cover")]
    report = {"at": now(), "considered": len(books), "matched": [], "unmatched": [], "errors": []}
    COVER_DIR.mkdir(parents=True, exist_ok=True)
    for index, book in enumerate(books):
        if book["title"].endswith("-samlingen") or book["author"] == "Ukjent":
            report["unmatched"].append({"title": book["title"], "reason": "collection-or-unknown-edition"})
            continue
        try:
            choices = google_candidates(book)
            choice = choices[0] if choices else None
            if not acceptable(choice):
                report["unmatched"].append({"title": book["title"], "best_candidate": choice})
                continue
            target = COVER_DIR / f"{book['id']}.jpg"
            dimensions = save_image(choice["image"], target)
            book["cover"] = f"/covers/{book['id']}.jpg"
            book["cover_match"] = {
                "provider": "Google Books",
                "provider_id": choice["google_books_id"],
                "isbn": choice["isbn"],
                "score": choice["score"],
                "matched_title": choice["title"],
                "matched_authors": choice["authors"],
                "at": now(),
            }
            save(c, book)
            report["matched"].append({"title": book["title"], "candidate": choice, **dimensions})
        except Exception as exc:
            report["errors"].append({"title": book["title"], "error": str(exc)})
        if index + 1 < len(books):
            time.sleep(0.12)
    snapshot(c)
    c.close()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report["matched_count"] = len(report["matched"])
    report["unmatched_count"] = len(report["unmatched"])
    report["error_count"] = len(report["errors"])
    path = REPORT_DIR / "physical-cover-matches.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: report[k] for k in ["considered", "matched_count", "unmatched_count", "error_count"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
