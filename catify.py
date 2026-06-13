import argparse
import sys
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from utils import (
    SUPPORTED_EXT, EXIFREAD_EXT, PILLOW_EXT, RAW_EXT, VIDEO_EXT,
    VERSION, ASCII_BANNER, DEFAULT_SANITIZE_MAX_LENGTH,
    file_sha256, get_size_str, get_mtime, sanitize_exif_dict,
)
from readers import (
    read_exif, read_exif_pillow, read_exif_pillow_gps,
    read_exif_raw, read_exif_video, read_exif_video_gps,
)
from extractors import (
    extract_gps, extract_gps_from_pillow,
    extract_thumbnail, extract_thumbnail_pillow,
)
from display import print_banner, print_rich_table, CONSOLE
from exporters import write_csv, write_json, write_html


def dispatch_read(path: Path, thumb_dir: Path):
    ext = path.suffix.lower()
    tags = {}
    gps = None
    thumb_path = ""

    if ext in EXIFREAD_EXT:
        raw_tags = read_exif(path)
        if raw_tags is None:
            return None, {}, None, ""
        if not raw_tags:
            return "no_exif", {}, None, ""
        tags = {str(k): str(v) for k, v in raw_tags.items()}
        gps = extract_gps(raw_tags)
        thumb_path = extract_thumbnail(raw_tags, path, thumb_dir)
        return "ok", tags, gps, thumb_path

    elif ext in PILLOW_EXT:
        raw_tags = read_exif_pillow(path)
        if raw_tags is None:
            return None, {}, None, ""
        if not raw_tags:
            return "no_exif", {}, None, ""
        gps = read_exif_pillow_gps(path)
        thumb_path = extract_thumbnail_pillow(path, thumb_dir)
        return "ok", raw_tags, gps, thumb_path

    elif ext in RAW_EXT:
        raw_tags = read_exif_raw(path)
        if raw_tags is None:
            return None, {}, None, ""
        if not raw_tags:
            return "no_exif", {}, None, ""
        return "ok", raw_tags, None, ""

    elif ext in VIDEO_EXT:
        raw_tags = read_exif_video(path)
        if raw_tags is None:
            return None, {}, None, ""
        if not raw_tags:
            return "no_exif", {}, None, ""
        gps = read_exif_video_gps(path)
        return "ok", raw_tags, gps, ""

    return None, {}, None, ""


def collect_files(input_path: str, recursive: bool) -> list:
    p = Path(input_path)
    if not p.exists():
        CONSOLE.print(f"[bold red][ERROR][/bold red] Path not found: {input_path}")
        sys.exit(1)
    if p.is_file():
        if p.suffix.lower() in SUPPORTED_EXT:
            return [p]
        CONSOLE.print(f"[bold red][ERROR][/bold red] Unsupported extension: {p.suffix}")
        sys.exit(1)
    files = []
    if recursive:
        for ext in SUPPORTED_EXT:
            files.extend(p.rglob(f"*{ext}"))
            files.extend(p.rglob(f"*{ext.upper()}"))
    else:
        for ext in SUPPORTED_EXT:
            files.extend(p.glob(f"*{ext}"))
            files.extend(p.glob(f"*{ext.upper()}"))
    return sorted(set(files))


def build_records(files: list, thumb_dir: Path, verbose: bool,
                   sanitize: bool = False,
                   sanitize_length: int = DEFAULT_SANITIZE_MAX_LENGTH) -> list:
    records = []
    hash_map = {}
    duplicate_hashes = set()

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("[dim]{task.fields[filename]}"),
        TimeElapsedColumn(),
        console=CONSOLE,
        transient=True,
    ) as progress:
        task = progress.add_task("Processing files...", total=len(files), filename="")

        for path in files:
            progress.update(task, advance=1, filename=path.name)
            if verbose:
                CONSOLE.print(f"  [dim]→ {path}[/dim]")

            sha = file_sha256(path)
            is_dup = False
            if sha:
                if sha in hash_map:
                    is_dup = True
                    duplicate_hashes.add(sha)
                else:
                    hash_map[sha] = str(path)

            status_result, exif_clean, gps, thumb_path = dispatch_read(path, thumb_dir)

            if status_result is None:
                status = "error"
                exif_clean = {}
            elif status_result == "no_exif":
                status = "no_exif"
                exif_clean = {}
            else:
                status = "ok"

            if sanitize and exif_clean:
                exif_clean = sanitize_exif_dict(exif_clean, sanitize_length)

            records.append({
                "file": path.name,
                "path": str(path.resolve()),
                "size": get_size_str(path),
                "mtime": get_mtime(path),
                "sha256": sha,
                "is_duplicate": is_dup,
                "duplicate_of": hash_map.get(sha, "") if is_dup else "",
                "status": status,
                "exif": exif_clean or {},
                "gps": gps,
                "thumbnail": thumb_path,
            })

    for rec in records:
        if rec["sha256"] in duplicate_hashes:
            rec["is_duplicate"] = True

    return records


def main():
    print_banner(ASCII_BANNER, VERSION)

    parser = argparse.ArgumentParser(
        prog="catify",
        description="Catify — EXIF Metadata Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  catify -i photo.jpg\n"
            "  catify -i ./photos -r --html report.html --json exif.json -v\n"
            "  catify -i ./photos -r --csv out.csv --html out.html --json out.json\n"
            "  catify -i ./photos -r --sanitize --sanitize-length 120\n"
        ),
    )
    parser.add_argument("-i", "--input", required=True, metavar="PATH",
                        help="File or directory path (required)")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="Search subdirectories")
    parser.add_argument("--csv", metavar="FILE", help="CSV output file")
    parser.add_argument("--html", metavar="FILE", help="HTML output file")
    parser.add_argument("--json", metavar="FILE", help="JSON output file")
    parser.add_argument("--thumbs", metavar="DIR", default="catify_thumbs",
                        help="Thumbnail output directory (default: catify_thumbs)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print each file name")
    parser.add_argument("--sanitize", action="store_true",
                        help="Sanitize EXIF tag/value strings before display and export (escapes non-printable characters and truncates long values)")
    parser.add_argument("--sanitize-length", type=int, default=DEFAULT_SANITIZE_MAX_LENGTH,
                        metavar="N",
                        help=f"Maximum visible length for sanitized EXIF values (default: {DEFAULT_SANITIZE_MAX_LENGTH}, requires --sanitize)")
    parser.add_argument("--version", action="version", version=f"Catify v{VERSION}")

    args = parser.parse_args()

    if args.sanitize_length < 1:
        CONSOLE.print("[bold red][ERROR][/bold red] --sanitize-length must be a positive integer")
        sys.exit(1)

    files = collect_files(args.input, args.recursive)
    if not files:
        CONSOLE.print("[yellow][INFO][/yellow] No supported files found.")
        sys.exit(0)

    CONSOLE.print(f"[dim]{len(files)} files found, processing…[/dim]\n")

    thumb_dir = Path(args.thumbs)
    records = build_records(
        files,
        thumb_dir,
        args.verbose,
        sanitize=args.sanitize,
        sanitize_length=args.sanitize_length,
    )

    print_rich_table(records)

    if args.csv:
        write_csv(records, args.csv)
    if args.json:
        write_json(records, args.json)
    if args.html:
        write_html(records, args.html, VERSION)

    CONSOLE.print()


if __name__ == "__main__":
    main()
