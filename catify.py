import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from datetime import datetime

try:
    import exifread
except ImportError:
    print("Missing: pip install exifread")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.text import Text
    from rich import box
    from rich.columns import Columns
    from rich.padding import Padding
except ImportError:
    print("Missing: pip install rich")
    sys.exit(1)

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import rawpy
    RAWPY_AVAILABLE = True
except ImportError:
    RAWPY_AVAILABLE = False

try:
    from pymediainfo import MediaInfo
    MEDIAINFO_AVAILABLE = True
except ImportError:
    MEDIAINFO_AVAILABLE = False

CONSOLE = Console()

VERSION = "2.0.0"

SUPPORTED_EXT = {
    ".jpg", ".jpeg", ".tiff", ".tif",
    ".png", ".webp", ".heic", ".heif",
    ".raw", ".cr2", ".cr3", ".nef", ".arw", ".dng",
    ".bmp", ".gif",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".mts", ".m2ts"
}

EXIFREAD_EXT = {".jpg", ".jpeg", ".tiff", ".tif"}
PILLOW_EXT   = {".png", ".webp", ".bmp", ".gif", ".heic", ".heif"}
RAW_EXT      = {".raw", ".cr2", ".cr3", ".nef", ".arw", ".dng"}
VIDEO_EXT    = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mts", ".m2ts"}

ASCII_BANNER = """
  /\\_____/\\
 /  o   o  \\
( ==  ^  == )
 )  C A T  (
(  I F Y   )
 \\ ExFin  /
  '-------'
"""

STATUS_OK = "[green]OK[/green]"
STATUS_NO_EXIF = "[yellow]NO EXIF[/yellow]"
STATUS_ERROR = "[red]ERROR[/red]"
STATUS_DUP = "[magenta]DUPLICATE[/magenta]"


def print_banner():
    CONSOLE.print(Panel(
        f"[bold cyan]{ASCII_BANNER}[/bold cyan]\n"
        f"[bold white]Catify[/bold white] [dim]v{VERSION}[/dim]  —  "
        f"[italic]EXIF Metadata Tool | @tc4dy[/italic]",
        border_style="cyan",
        expand=False,
    ))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def get_size_str(path: Path) -> str:
    try:
        size = path.stat().st_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except Exception:
        return "N/A"


def get_mtime(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "N/A"


def dms_to_decimal(values, ref) -> float:
    def ratio_to_float(r):
        parts = str(r).split("/")
        if len(parts) == 2:
            return float(parts[0]) / float(parts[1]) if float(parts[1]) != 0 else 0.0
        return float(parts[0])
    try:
        degrees = ratio_to_float(values[0])
        minutes = ratio_to_float(values[1])
        seconds = ratio_to_float(values[2])
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
        if ref in ("S", "W"):
            decimal = -decimal
        return round(decimal, 7)
    except Exception:
        return 0.0


def extract_gps(tags: dict):
    try:
        lat_tag = tags.get("GPS GPSLatitude")
        lat_ref = str(tags.get("GPS GPSLatitudeRef", "N"))
        lon_tag = tags.get("GPS GPSLongitude")
        lon_ref = str(tags.get("GPS GPSLongitudeRef", "E"))
        if not lat_tag or not lon_tag:
            return None
        lat_vals = lat_tag.values
        lon_vals = lon_tag.values
        lat = dms_to_decimal(lat_vals, lat_ref)
        lon = dms_to_decimal(lon_vals, lon_ref)
        if lat == 0.0 and lon == 0.0:
            return None
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        osm_url = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=15"
        return {"lat": lat, "lon": lon, "google_maps": maps_url, "openstreetmap": osm_url}
    except Exception:
        return None


def extract_gps_from_pillow(gps_data: dict):
    try:
        def to_decimal(vals, ref):
            d = float(vals[0])
            m = float(vals[1])
            s = float(vals[2])
            result = d + m / 60.0 + s / 3600.0
            if ref in ("S", "W"):
                result = -result
            return round(result, 7)

        lat = to_decimal(gps_data.get(2, (0, 0, 0)), gps_data.get(1, "N"))
        lon = to_decimal(gps_data.get(4, (0, 0, 0)), gps_data.get(3, "E"))
        if lat == 0.0 and lon == 0.0:
            return None
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        osm_url = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=15"
        return {"lat": lat, "lon": lon, "google_maps": maps_url, "openstreetmap": osm_url}
    except Exception:
        return None


def extract_thumbnail(tags: dict, path: Path, thumb_dir: Path) -> str:
    try:
        with open(path, "rb") as f:
            raw = exifread.process_file(f, details=True)
        thumb = raw.get("JPEGThumbnail") or raw.get("TIFFThumbnail")
        if thumb is None:
            return ""
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / f"{path.stem}_thumb.jpg"
        with open(thumb_path, "wb") as tf:
            tf.write(thumb)
        return str(thumb_path.resolve())
    except Exception:
        return ""


def extract_thumbnail_pillow(path: Path, thumb_dir: Path) -> str:
    try:
        img = Image.open(path)
        img.thumbnail((160, 160))
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / f"{path.stem}_thumb.jpg"
        img.convert("RGB").save(thumb_path, "JPEG")
        return str(thumb_path.resolve())
    except Exception:
        return ""


def read_exif(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, details=False)
        return tags if tags else {}
    except Exception:
        return None


def read_exif_pillow(path: Path) -> dict:
    if not PILLOW_AVAILABLE:
        return None
    try:
        img = Image.open(path)
        raw = None
        try:
            exif_obj = img.getexif()
            raw = dict(exif_obj) if exif_obj else None
        except Exception:
            pass
        if not raw:
            try:
                raw = img._getexif()
            except Exception:
                pass
        if not raw:
            return {}
        result = {}
        for tag_id, value in raw.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            if tag_name == "GPSInfo":
                continue
            try:
                result[f"Image {tag_name}"] = str(value)
            except Exception:
                pass
        return result
    except Exception:
        return None


def read_exif_pillow_gps(path: Path):
    if not PILLOW_AVAILABLE:
        return None
    try:
        img = Image.open(path)
        raw = None
        try:
            exif_obj = img.getexif()
            raw = dict(exif_obj) if exif_obj else None
        except Exception:
            pass
        if not raw:
            try:
                raw = img._getexif()
            except Exception:
                pass
        if not raw:
            return None
        for tag_id, value in raw.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            if tag_name == "GPSInfo":
                gps = {}
                for k, v in value.items():
                    gps[k] = v
                return extract_gps_from_pillow(gps)
        return None
    except Exception:
        return None


def read_exif_raw(path: Path) -> dict:
    if not RAWPY_AVAILABLE:
        return None
    try:
        with rawpy.imread(str(path)) as raw:
            tags = {}
            try:
                tags["Image Make"] = str(raw.metadata.camera_manufacturer or "")
            except Exception:
                pass
            try:
                tags["Image Model"] = str(raw.metadata.camera_model or "")
            except Exception:
                pass
            try:
                ts = raw.metadata.timestamp
                if ts:
                    tags["Image DateTime"] = str(datetime.fromtimestamp(ts).strftime("%Y:%m:%d %H:%M:%S"))
            except Exception:
                pass
            try:
                tags["Image ISO"] = str(raw.metadata.iso)
            except Exception:
                pass
            try:
                tags["Image ShutterSpeed"] = str(raw.metadata.shutter)
            except Exception:
                pass
            try:
                tags["Image Aperture"] = str(raw.metadata.aperture)
            except Exception:
                pass
            try:
                tags["Image FocalLen"] = str(raw.metadata.focal_len)
            except Exception:
                pass
            try:
                tags["Image Width"] = str(raw.sizes.width)
                tags["Image Height"] = str(raw.sizes.height)
            except Exception:
                pass
        return {k: v for k, v in tags.items() if v and v != "None"}
    except Exception:
        return None


def read_exif_video(path: Path) -> dict:
    if not MEDIAINFO_AVAILABLE:
        return None
    try:
        info = MediaInfo.parse(str(path))
        result = {}
        for track in info.tracks:
            prefix = track.track_type
            for key, val in track.to_data().items():
                if val is not None and str(val).strip():
                    result[f"{prefix} {key}"] = str(val)
        return result if result else {}
    except Exception:
        return None


def read_exif_video_gps(path: Path):
    if not MEDIAINFO_AVAILABLE:
        return None
    try:
        info = MediaInfo.parse(str(path))
        for track in info.tracks:
            data = track.to_data()
            lat = data.get("comapplequicktimegpslocation") or data.get("gps_position")
            if lat:
                parts = str(lat).replace("+", " +").replace("-", " -").split()
                parts = [p for p in parts if p]
                if len(parts) >= 2:
                    try:
                        la = float(parts[0])
                        lo = float(parts[1])
                        if la != 0.0 or lo != 0.0:
                            maps_url = f"https://www.google.com/maps?q={la},{lo}"
                            osm_url = f"https://www.openstreetmap.org/?mlat={la}&mlon={lo}&zoom=15"
                            return {"lat": la, "lon": lo, "google_maps": maps_url, "openstreetmap": osm_url}
                    except Exception:
                        pass
        return None
    except Exception:
        return None


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
        if not PILLOW_AVAILABLE:
            return None, {}, None, ""
        raw_tags = read_exif_pillow(path)
        if raw_tags is None:
            return None, {}, None, ""
        if not raw_tags:
            return "no_exif", {}, None, ""
        gps = read_exif_pillow_gps(path)
        thumb_path = extract_thumbnail_pillow(path, thumb_dir)
        return "ok", raw_tags, gps, thumb_path

    elif ext in RAW_EXT:
        if not RAWPY_AVAILABLE:
            return None, {}, None, ""
        raw_tags = read_exif_raw(path)
        if raw_tags is None:
            return None, {}, None, ""
        if not raw_tags:
            return "no_exif", {}, None, ""
        return "ok", raw_tags, None, ""

    elif ext in VIDEO_EXT:
        if not MEDIAINFO_AVAILABLE:
            return None, {}, None, ""
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


def build_records(files: list, thumb_dir: Path, verbose: bool) -> list:
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


def print_rich_table(records: list):
    CONSOLE.print()

    stats_ok = sum(1 for r in records if r["status"] == "ok")
    stats_noexif = sum(1 for r in records if r["status"] == "no_exif")
    stats_err = sum(1 for r in records if r["status"] == "error")
    stats_dup = sum(1 for r in records if r["is_duplicate"])
    stats_gps = sum(1 for r in records if r["gps"])
    stats_thumb = sum(1 for r in records if r["thumbnail"])

    summary = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    summary.add_column(style="dim")
    summary.add_column(style="bold")
    summary.add_row("Total files", str(len(records)))
    summary.add_row("EXIF OK", f"[green]{stats_ok}[/green]")
    summary.add_row("No EXIF", f"[yellow]{stats_noexif}[/yellow]")
    summary.add_row("Error", f"[red]{stats_err}[/red]")
    summary.add_row("Duplicate", f"[magenta]{stats_dup}[/magenta]")
    summary.add_row("With GPS", f"[cyan]{stats_gps}[/cyan]")
    summary.add_row("Thumbnail", f"[blue]{stats_thumb}[/blue]")

    CONSOLE.print(Panel(summary, title="[bold white]Summary[/bold white]", border_style="white", expand=False))
    CONSOLE.print()

    for rec in records:
        status_tag = {
            "ok": STATUS_OK,
            "no_exif": STATUS_NO_EXIF,
            "error": STATUS_ERROR,
        }.get(rec["status"], STATUS_ERROR)

        dup_tag = f"  {STATUS_DUP}" if rec["is_duplicate"] else ""

        header = Table.grid(padding=(0, 1))
        header.add_column(style="bold white", min_width=30)
        header.add_column()
        header.add_row(f"[bold cyan]{rec['file']}[/bold cyan]", f"{status_tag}{dup_tag}")
        header.add_row(f"[dim]{rec['path']}[/dim]", "")
        header.add_row(f"Size: [white]{rec['size']}[/white]  Date: [white]{rec['mtime']}[/white]", "")
        header.add_row(f"[dim]SHA256: {rec['sha256'][:16]}…[/dim]", "")

        if rec["is_duplicate"] and rec["duplicate_of"]:
            header.add_row(f"[magenta]Same file: {rec['duplicate_of']}[/magenta]", "")

        if rec["gps"]:
            g = rec["gps"]
            header.add_row(
                f"[cyan]GPS: {g['lat']}, {g['lon']}[/cyan]  "
                f"[link={g['google_maps']}][underline]Google Maps[/underline][/link]  "
                f"[link={g['openstreetmap']}][underline]OSM[/underline][/link]",
                "",
            )

        if rec["thumbnail"]:
            header.add_row(f"[blue]Thumbnail: {rec['thumbnail']}[/blue]", "")

        inner_panels = [Panel(header, expand=True, border_style="dim")]

        if rec["status"] == "ok" and rec["exif"]:
            exif_table = Table(
                box=box.SIMPLE_HEAD,
                show_header=True,
                header_style="bold magenta",
                padding=(0, 1),
                expand=True,
            )
            exif_table.add_column("Tag", style="cyan", min_width=35, no_wrap=True)
            exif_table.add_column("Value", style="white", overflow="fold")
            for tag, val in sorted(rec["exif"].items()):
                clean_tag = tag.replace("EXIF ", "").replace("Image ", "").replace("GPS ", "GPS ")
                exif_table.add_row(clean_tag, val)
            inner_panels.append(Panel(exif_table, title="[bold]EXIF[/bold]", border_style="dim"))

        CONSOLE.print(Panel(
            Columns(inner_panels, equal=False, expand=True),
            border_style="cyan",
            padding=(0, 1),
        ))
        CONSOLE.print()


def write_csv(records: list, output_path: str):
    all_tags = sorted({tag for r in records for tag in r["exif"].keys()})
    try:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            base_cols = ["file", "path", "size", "mtime", "sha256", "is_duplicate",
                         "duplicate_of", "status", "gps_lat", "gps_lon",
                         "google_maps", "openstreetmap", "thumbnail"]
            writer.writerow(base_cols + all_tags)
            for rec in records:
                g = rec["gps"] or {}
                base = [
                    rec["file"], rec["path"], rec["size"], rec["mtime"],
                    rec["sha256"], rec["is_duplicate"], rec["duplicate_of"],
                    rec["status"],
                    g.get("lat", ""), g.get("lon", ""),
                    g.get("google_maps", ""), g.get("openstreetmap", ""),
                    rec["thumbnail"],
                ]
                exif_vals = [rec["exif"].get(t, "") for t in all_tags]
                writer.writerow(base + exif_vals)
        CONSOLE.print(f"[green][CSV][/green] Saved: {output_path}")
    except Exception as e:
        CONSOLE.print(f"[red][CSV ERROR][/red] {e}")


def write_json(records: list, output_path: str):
    out = []
    for rec in records:
        out.append({
            "file": rec["file"],
            "path": rec["path"],
            "size": rec["size"],
            "mtime": rec["mtime"],
            "sha256": rec["sha256"],
            "is_duplicate": rec["is_duplicate"],
            "duplicate_of": rec["duplicate_of"],
            "status": rec["status"],
            "gps": rec["gps"],
            "thumbnail": rec["thumbnail"],
            "exif": rec["exif"],
        })
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        CONSOLE.print(f"[green][JSON][/green] Saved: {output_path}")
    except Exception as e:
        CONSOLE.print(f"[red][JSON ERROR][/red] {e}")


def write_html(records: list, output_path: str):
    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    rows_html = []
    for i, rec in enumerate(records):
        bg_class = "row-even" if i % 2 == 0 else "row-odd"

        badges = ""
        status_map = {
            "ok": '<span class="badge badge-ok">OK</span>',
            "no_exif": '<span class="badge badge-warn">NO EXIF</span>',
            "error": '<span class="badge badge-err">ERROR</span>',
        }
        badges += status_map.get(rec["status"], "")
        if rec["is_duplicate"]:
            badges += '<span class="badge badge-dup">DUPLICATE</span>'

        gps_html = ""
        if rec["gps"]:
            g = rec["gps"]
            gps_html = (
                f'<div class="gps-block">'
                f'📍 {g["lat"]}, {g["lon"]}&nbsp;&nbsp;'
                f'<a href="{esc(g["google_maps"])}" target="_blank">Google Maps</a> · '
                f'<a href="{esc(g["openstreetmap"])}" target="_blank">OSM</a>'
                f'</div>'
            )

        dup_html = ""
        if rec["is_duplicate"] and rec["duplicate_of"]:
            dup_html = f'<div class="dup-block">Same file: <code>{esc(rec["duplicate_of"])}</code></div>'

        thumb_html = ""
        if rec["thumbnail"]:
            thumb_html = f'<div class="thumb-block">🖼 Thumbnail: <code>{esc(rec["thumbnail"])}</code></div>'

        exif_html = ""
        if rec["status"] == "ok" and rec["exif"]:
            rows = ""
            for j, (tag, val) in enumerate(sorted(rec["exif"].items())):
                tr_class = "er" if j % 2 == 0 else ""
                clean = esc(tag.replace("EXIF ", "").replace("Image ", ""))
                rows += f'<tr class="{tr_class}"><td class="tag-col">{clean}</td><td>{esc(val)}</td></tr>'
            exif_html = (
                f'<table class="exif-table"><thead><tr>'
                f'<th>Tag</th><th>Value</th>'
                f'</tr></thead><tbody>{rows}</tbody></table>'
            )
        elif rec["status"] == "no_exif":
            exif_html = '<p class="no-exif-msg">No EXIF data found in this file.</p>'
        elif rec["status"] == "error":
            exif_html = '<p class="err-msg">Cannot read file.</p>'

        sha_short = rec["sha256"][:16] + "…" if rec["sha256"] else "N/A"

        rows_html.append(f"""
        <div class="file-card {bg_class}">
          <div class="file-header">
            <div class="file-title">
              <span class="filename">{esc(rec['file'])}</span>
              <span class="badges">{badges}</span>
            </div>
            <div class="file-meta">
              <span class="meta-item">📁 {esc(rec['path'])}</span>
              <span class="meta-item">📦 {esc(rec['size'])}</span>
              <span class="meta-item">🕐 {esc(rec['mtime'])}</span>
              <span class="meta-item mono">🔑 {sha_short}</span>
            </div>
            {gps_html}{dup_html}{thumb_html}
          </div>
          <div class="exif-section">{exif_html}</div>
        </div>""")

    content = "\n".join(rows_html)

    total = len(records)
    ok_c = sum(1 for r in records if r["status"] == "ok")
    dup_c = sum(1 for r in records if r["is_duplicate"])
    gps_c = sum(1 for r in records if r["gps"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Catify — EXIF Report</title>
<style>
:root {{
  --bg: #0d1117; --surface: #161b22; --surface2: #1c2128;
  --border: #30363d; --accent: #58a6ff; --accent2: #f78166;
  --green: #3fb950; --yellow: #d29922; --red: #f85149;
  --magenta: #bc8cff; --text: #c9d1d9; --muted: #8b949e;
  --font-mono: 'SFMono-Regular', 'Consolas', monospace;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; line-height: 1.5; padding: 24px; }}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.mono {{ font-family: var(--font-mono); font-size: 12px; }}
header {{ border-bottom: 1px solid var(--border); padding-bottom: 20px; margin-bottom: 24px; }}
.logo {{ font-family: var(--font-mono); font-size: 22px; font-weight: 700; color: var(--accent); letter-spacing: 3px; }}
.subtitle {{ color: var(--muted); font-size: 13px; margin-top: 4px; }}
.stats {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 20px 0 28px; }}
.stat-box {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 18px; min-width: 100px; }}
.stat-box .num {{ font-size: 26px; font-weight: 700; font-family: var(--font-mono); }}
.stat-box .lbl {{ font-size: 11px; color: var(--muted); margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }}
.file-card {{ border: 1px solid var(--border); border-radius: 10px; margin-bottom: 16px; overflow: hidden; }}
.row-even {{ background: var(--surface); }}
.row-odd {{ background: var(--surface2); }}
.file-header {{ padding: 14px 18px; border-bottom: 1px solid var(--border); }}
.file-title {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }}
.filename {{ font-weight: 700; font-size: 15px; color: #fff; font-family: var(--font-mono); }}
.badges {{ display: flex; gap: 6px; flex-wrap: wrap; }}
.badge {{ display: inline-block; border-radius: 4px; padding: 1px 8px; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; }}
.badge-ok {{ background: #1a3a1a; color: var(--green); border: 1px solid var(--green); }}
.badge-warn {{ background: #2d2a0a; color: var(--yellow); border: 1px solid var(--yellow); }}
.badge-err {{ background: #2d1010; color: var(--red); border: 1px solid var(--red); }}
.badge-dup {{ background: #1e1a2d; color: var(--magenta); border: 1px solid var(--magenta); }}
.file-meta {{ display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--muted); }}
.meta-item {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 500px; }}
.gps-block {{ margin-top: 8px; font-size: 12px; color: #79c0ff; }}
.dup-block {{ margin-top: 6px; font-size: 12px; color: var(--magenta); }}
.thumb-block {{ margin-top: 6px; font-size: 12px; color: #7ee787; }}
.exif-section {{ padding: 0 18px 14px; }}
.exif-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }}
.exif-table thead tr {{ background: #0d1117; }}
.exif-table th {{ text-align: left; padding: 6px 10px; color: var(--magenta); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); }}
.exif-table td {{ padding: 4px 10px; vertical-align: top; border-bottom: 1px solid #21262d; word-break: break-word; }}
.exif-table tr.er td {{ background: rgba(255,255,255,0.02); }}
.tag-col {{ color: var(--accent); font-family: var(--font-mono); white-space: nowrap; width: 38%; }}
.no-exif-msg {{ color: var(--yellow); padding: 10px 0; font-size: 12px; }}
.err-msg {{ color: var(--red); padding: 10px 0; font-size: 12px; }}
footer {{ margin-top: 32px; border-top: 1px solid var(--border); padding-top: 12px; color: var(--muted); font-size: 11px; text-align: center; }}
@media (max-width: 600px) {{ .file-meta {{ flex-direction: column; }} .stats {{ gap: 8px; }} }}
</style>
</head>
<body>
<header>
  <div class="logo">🐱 CATIFY</div>
  <div class="subtitle">ExFin Tool — EXIF Metadata Report</div>
</header>
<div class="stats">
  <div class="stat-box"><div class="num" style="color:var(--accent)">{total}</div><div class="lbl">Total Files</div></div>
  <div class="stat-box"><div class="num" style="color:var(--green)">{ok_c}</div><div class="lbl">EXIF OK</div></div>
  <div class="stat-box"><div class="num" style="color:var(--magenta)">{dup_c}</div><div class="lbl">Duplicate</div></div>
  <div class="stat-box"><div class="num" style="color:#79c0ff">{gps_c}</div><div class="lbl">With GPS</div></div>
</div>
{content}
<footer>Catify v{VERSION} · Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</footer>
</body>
</html>"""

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        CONSOLE.print(f"[green][HTML][/green] Saved: {output_path}")
    except Exception as e:
        CONSOLE.print(f"[red][HTML ERROR][/red] {e}")


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        prog="catify",
        description="Catify — EXIF Metadata Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  catify -i photo.jpg\n"
            "  catify -i ./photos -r --html report.html --json exif.json -v\n"
            "  catify -i ./photos -r --csv out.csv --html out.html --json out.json\n"
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
    parser.add_argument("--version", action="version", version=f"Catify v{VERSION}")

    args = parser.parse_args()

    files = collect_files(args.input, args.recursive)
    if not files:
        CONSOLE.print("[yellow][INFO][/yellow] No supported files found.")
        sys.exit(0)

    CONSOLE.print(f"[dim]{len(files)} files found, processing…[/dim]\n")

    thumb_dir = Path(args.thumbs)
    records = build_records(files, thumb_dir, args.verbose)

    print_rich_table(records)

    if args.csv:
        write_csv(records, args.csv)
    if args.json:
        write_json(records, args.json)
    if args.html:
        write_html(records, args.html)

    CONSOLE.print()


if __name__ == "__main__":
    main()
