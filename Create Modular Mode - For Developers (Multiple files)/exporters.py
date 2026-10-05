import csv
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console

CONSOLE = Console()


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


def write_html(records: list, output_path: str, version: str):
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
<footer>Catify v{version} · Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</footer>
</body>
</html>"""

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        CONSOLE.print(f"[green][HTML][/green] Saved: {output_path}")
    except Exception as e:
        CONSOLE.print(f"[red][HTML ERROR][/red] {e}")