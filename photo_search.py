#!/usr/bin/env python3
"""
Photo library indexer and searcher using Claude's vision API.

Usage:
  python photo_search.py index ~/Photos           # index all photos
  python photo_search.py index ~/Photos --force   # re-index everything
  python photo_search.py search ~/Photos "kids at the beach"
  python photo_search.py stats ~/Photos
"""

import anthropic
import argparse
import base64
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
INDEX_FILE = ".photo_index.json"
MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


# ─── Index helpers ────────────────────────────────────────────────────────────

def load_index(index_path: Path) -> dict:
    if index_path.exists():
        return json.loads(index_path.read_text())
    return {}


def save_index(index_path: Path, index: dict) -> None:
    index_path.write_text(json.dumps(index, indent=2))


# ─── Image encoding ───────────────────────────────────────────────────────────

def encode_image(image_path: Path) -> tuple[str, str]:
    """
    Read and base64-encode an image. Resizes large images with Pillow if
    available, so we don't waste tokens on megapixel photos.
    """
    ext = image_path.suffix.lower()
    media_type = MEDIA_TYPES.get(ext, "image/jpeg")
    data = image_path.read_bytes()

    try:
        from PIL import Image  # type: ignore
        import io

        img = Image.open(io.BytesIO(data))
        max_dim = 1568  # Claude vision optimal max dimension
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
            buf = io.BytesIO()
            save_fmt = "JPEG" if ext in (".jpg", ".jpeg") else (img.format or "PNG")
            if save_fmt == "JPEG" and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(buf, format=save_fmt)
            data = buf.getvalue()
            if save_fmt == "JPEG":
                media_type = "image/jpeg"
    except ImportError:
        pass  # Pillow not installed — use original bytes

    return base64.standard_b64encode(data).decode("utf-8"), media_type


# ─── Claude calls ─────────────────────────────────────────────────────────────

DESCRIBE_PROMPT = """\
Describe this photo in rich detail for search purposes. Cover:
- Main subjects (people, animals, objects)
- Setting / location / environment
- Colors and lighting
- Activities or actions
- Mood or atmosphere
- Any visible text or signs
- Time of day or season if apparent
- Any notable or unique features

Be specific so the description enables accurate text-based searching later.\
"""


def describe_image(client: anthropic.Anthropic, image_path: Path) -> str:
    """Send an image to Claude and return its description."""
    image_data, media_type = encode_image(image_path)

    stream = client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": DESCRIBE_PROMPT},
                ],
            }
        ],
    )
    return stream.get_final_message().content[0].text


SEARCH_PROMPT_TEMPLATE = """\
I have a photo library. Here are the indexed photos and their descriptions:

{catalog}

Search query: "{query}"

Find the {max_results} most relevant photos that match this query.
Return ONLY a JSON array — no markdown fences, no explanation — in this exact format:
[
  {{"rank": 1, "path": "relative/path/to/photo.jpg", "reason": "brief explanation"}},
  ...
]
If fewer than {max_results} match, return only the matching ones.
If none match, return an empty array: []\
"""


def search_index(
    client: anthropic.Anthropic,
    index: dict,
    query: str,
    max_results: int,
) -> list[dict]:
    """Ask Claude to rank stored descriptions against a free-text query."""
    catalog = "\n\n".join(
        f"Photo {i + 1}: {rel_path}\nDescription: {entry['description']}"
        for i, (rel_path, entry) in enumerate(index.items())
    )

    prompt = SEARCH_PROMPT_TEMPLATE.format(
        catalog=catalog, query=query, max_results=max_results
    )

    stream = client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )
    response = stream.get_final_message()

    # Extract text block (skip thinking blocks)
    result_text = next(
        (b.text for b in response.content if b.type == "text"), ""
    )

    # Pull out the JSON array even if wrapped in stray text
    json_match = re.search(r"\[.*\]", result_text, re.DOTALL)
    raw = json_match.group() if json_match else result_text
    return json.loads(raw)


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_index(client: anthropic.Anthropic, directory: Path, force: bool) -> None:
    index_path = directory / INDEX_FILE
    index = load_index(index_path)

    image_files = sorted(
        f
        for f in directory.rglob("*")
        if f.suffix.lower() in SUPPORTED_EXTENSIONS and not f.name.startswith(".")
    )

    if not image_files:
        print(f"No supported images found in {directory}")
        return

    print(f"Found {len(image_files)} image(s).")

    new_count = skipped_count = error_count = 0

    for i, image_path in enumerate(image_files, 1):
        rel_path = str(image_path.relative_to(directory))

        if not force and rel_path in index:
            skipped_count += 1
            continue

        print(f"  [{i}/{len(image_files)}] {rel_path} … ", end="", flush=True)
        try:
            description = describe_image(client, image_path)
            index[rel_path] = {
                "description": description,
                "indexed_at": datetime.now().isoformat(),
                "file_size": image_path.stat().st_size,
            }
            save_index(index_path, index)
            new_count += 1
            print("done")
        except Exception as exc:
            error_count += 1
            print(f"ERROR: {exc}")

    print(
        f"\nIndexed {new_count} new  |  skipped {skipped_count} (already done)"
        f"  |  {error_count} error(s)"
    )
    print(f"Index: {index_path}")


def cmd_search(
    client: anthropic.Anthropic,
    directory: Path,
    query: str,
    max_results: int,
) -> None:
    index_path = directory / INDEX_FILE
    index = load_index(index_path)

    if not index:
        print("No photos indexed yet — run the 'index' command first.")
        return

    print(f"Searching {len(index)} photo(s) for: \"{query}\"\n")

    try:
        results = search_index(client, index, query, max_results)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Could not parse Claude's response: {exc}")
        return

    if not results:
        print("No matching photos found.")
        return

    print(f"Found {len(results)} match(es):\n")
    for r in results:
        path = r.get("path", "?")
        rank = r.get("rank", "?")
        reason = r.get("reason", "")
        full = directory / path
        print(f"  {rank}. {path}")
        if reason:
            print(f"     {reason}")
        print(f"     → {full}")
        print()


def cmd_stats(directory: Path) -> None:
    index_path = directory / INDEX_FILE
    index = load_index(index_path)

    if not index:
        print("No photos indexed yet.")
        return

    dates = sorted(e.get("indexed_at", "") for e in index.values() if e.get("indexed_at"))
    print(f"Directory : {directory}")
    print(f"Index file: {index_path}")
    print(f"Photos    : {len(index)}")
    if dates:
        print(f"First indexed : {dates[0][:19]}")
        print(f"Last indexed  : {dates[-1][:19]}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Index and search your photo library with Claude's vision API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python photo_search.py index ~/Photos
  python photo_search.py index ~/Photos --force
  python photo_search.py search ~/Photos "sunset at the beach"
  python photo_search.py search ~/Photos "birthday party" --max-results 10
  python photo_search.py stats ~/Photos
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # index
    p_index = sub.add_parser("index", help="Index photos in a directory")
    p_index.add_argument("directory", type=Path, help="Directory to scan")
    p_index.add_argument(
        "--force", action="store_true", help="Re-index already-indexed photos"
    )

    # search
    p_search = sub.add_parser("search", help="Search indexed photos by description")
    p_search.add_argument("directory", type=Path, help="Indexed photo directory")
    p_search.add_argument("query", help='What to search for, e.g. "dog on beach"')
    p_search.add_argument(
        "--max-results", type=int, default=5, metavar="N",
        help="Maximum results to return (default: 5)",
    )

    # stats
    p_stats = sub.add_parser("stats", help="Show index statistics")
    p_stats.add_argument("directory", type=Path, help="Indexed photo directory")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.directory.is_dir():
        parser.error(f"'{args.directory}' is not a directory or does not exist.")

    if args.command == "stats":
        cmd_stats(args.directory)
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    if args.command == "index":
        cmd_index(client, args.directory, force=args.force)
    elif args.command == "search":
        cmd_search(client, args.directory, args.query, max_results=args.max_results)


if __name__ == "__main__":
    main()
