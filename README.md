![Catify](https://raw.githubusercontent.com/tc4dy/Catify/main/catify.jpg)

# 🐱 Catify – EXIF Metadata Tool

**Catify** is a powerful command-line tool to extract, analyze, and report metadata from images, RAW files, and videos. It detects duplicate files via SHA256, extracts GPS coordinates with direct map links, saves embedded thumbnails, and generates beautiful terminal output or export reports in CSV, JSON, or HTML.

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Core Deps](https://img.shields.io/badge/core-exifread%20%7C%20rich-orange)]()
[![Optional Deps](https://img.shields.io/badge/optional-Pillow%20%7C%20rawpy%20%7C%20pymediainfo-lightgrey)]()

---

## ✨ Features

| Feature | Description |
|---|---|
| 📸 Full metadata extraction | Camera make, model, exposure, ISO, datetime, dimensions, and more |
| 🌍 GPS extraction | Converts DMS to decimal, provides Google Maps & OpenStreetMap links |
| 🔍 Duplicate detection | SHA256 hash comparison across files |
| 🖼️ Thumbnail extraction | Saves embedded thumbnails to a separate directory |
| 📊 Rich terminal output | Colorful tables with live progress bar (via `rich`) |
| 📄 Multiple export formats | CSV, JSON, HTML (viewable in any browser) |
| 🚀 Recursive scanning | Process entire folder trees |
| 🧹 Clean & fast | Handles large files efficiently with graceful error handling |

---

## 🖼️ Supported Formats

| Category | Extensions | Reader Used |
|---|---|---|
| **Images** | `.jpg` `.jpeg` `.tiff` `.tif` | `exifread` (full EXIF + thumbnails + GPS) |
| **Common image formats** | `.png` `.webp` `.bmp` `.gif` `.heic` `.heif` | `Pillow` (EXIF + GPS + thumbnails) |
| **RAW formats** | `.raw` `.cr2` `.cr3` `.nef` `.arw` `.dng` | `rawpy` (camera, ISO, exposure, dimensions) |
| **Video formats** | `.mp4` `.mov` `.avi` `.mkv` `.webm` `.mts` `.m2ts` | `pymediainfo` (track metadata + GPS) |

> ⚠️ Formats outside the `exifread`/core set require the matching **optional dependency** below. If it's missing, those files will be reported with `ERROR` status instead of being processed.

---

## 📦 Installation

### Option 1 — Download the full release 🚀

👉 https://github.com/tc4dy/Catify/releases/tag/Catify

### Option 2 — Clone the repo

```bash
git clone https://github.com/tc4dy/Catify.git
cd Catify
```

### Install dependencies

| Dependency | Required? | Enables |
|---|---|---|
| `exifread` | ✅ Required | JPEG/TIFF EXIF parsing |
| `rich` | ✅ Required | Terminal tables, colors, progress bar |
| `Pillow` | ⚙️ Optional | PNG, WEBP, BMP, GIF, HEIC, HEIF support |
| `rawpy` | ⚙️ Optional | RAW format support (CR2, NEF, ARW, DNG...) |
| `pymediainfo` | ⚙️ Optional | Video metadata & GPS support |

**Minimal (JPEG/TIFF only):**

```bash
pip install exifread rich
```

**Full (all formats):**

```bash
pip install exifread rich pillow rawpy pymediainfo
```

> 💡 `pymediainfo` also requires the **MediaInfo** library to be installed on your system (e.g. `apt install mediainfo` on Debian/Ubuntu, or `brew install media-info` on macOS).

### Run the tool

```bash
python catify.py --help
```

---

## 🚀 Usage

```bash
python catify.py -i <INPUT> [OPTIONS]
```

### Required argument

| Argument | Description |
|---|---|
| `-i`, `--input PATH` | Path to a single file or a directory |

### Optional arguments

| Option | Description |
|---|---|
| `-r`, `--recursive` | Scan subdirectories recursively |
| `--csv FILE` | Export report to CSV format |
| `--json FILE` | Export report to JSON format |
| `--html FILE` | Export report to HTML format |
| `--thumbs DIR` | Directory to save thumbnails (default: `catify_thumbs`) |
| `-v`, `--verbose` | Print each file name while processing |
| `--version` | Show version information |

---

## 📖 Examples

**Analyze a single image**

```bash
python catify.py -i vacation.jpg
```

**Scan a folder (including subfolders) and generate an HTML report**

```bash
python catify.py -i ./photos -r --html report.html
```

**Full export: CSV, JSON, HTML, with custom thumbnail directory and verbose output**

```bash
python catify.py -i ./images -r --csv metadata.csv --json exif.json --html report.html --thumbs my_thumbs -v
```

**Only show terminal output (no exports)**

```bash
python catify.py -i DSC_001.jpg
```

---

## 📊 Output Examples

### Terminal (Rich Table)

```
  /\_____/\
 /  o   o  \
( ==  ^  == )
 )  C A T  (
(  I F Y   )
 \ ExFin  /
  '-------'
Catify v2.0.0 — EXIF Metadata Tool | @tc4dy

5 files found, processing…

┌───────────────────────────── Summary ──────────────────────────────┐
│  Total files   5                                                    │
│  EXIF OK       4                                                    │
│  No EXIF       0                                                    │
│  Error         1                                                    │
│  Duplicate     2                                                    │
│  With GPS      1                                                    │
│  Thumbnail     3                                                    │
└───────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  photo.jpg                               OK   DUPLICATE              │
│  /home/user/photos/photo.jpg                                         │
│  Size: 2.3 MB  Date: 2024-01-15 14:32:10                             │
│  SHA256: a1b2c3d4e5f6…                                               │
│  Same file: /backup/photo.jpg                                        │
│  GPS: 41.0082, 28.9784  Google Maps  OSM                             │
│  Thumbnail: catify_thumbs/photo_thumb.jpg                            │
│                                                                       │
│  ┌──────────────────────────── EXIF ──────────────────────────────┐ │
│  │ Tag                    Value                                    │ │
│  ├──────────────────────────────────────────────────────────────  │ │
│  │ Image Make             Canon                                    │ │
│  │ Image Model            EOS 5D                                   │ │
│  │ EXIF ExposureTime      1/125                                    │ │
│  │ EXIF FNumber           2.8                                      │ │
│  │ EXIF ISO               100                                      │ │
│  └──────────────────────────────────────────────────────────────  │ │
└─────────────────────────────────────────────────────────────────────┘
```

### Status Badges

| Badge | Meaning |
|---|---|
| 🟢 `OK` | Metadata read successfully |
| 🟡 `NO EXIF` | File readable, but no metadata found |
| 🔴 `ERROR` | File couldn't be read (missing dependency or corrupt file) |
| 🟣 `DUPLICATE` | File content matches another file (same SHA256) |

### HTML Report

Open the generated `.html` file in any browser. It includes:

- 📊 Summary statistics cards (total files, OK, duplicates, GPS)
- 🗂️ Each file with metadata table, GPS links, and thumbnail path
- 🌑 Dark theme, responsive layout

### CSV Export

All metadata tags become columns — perfect for Excel or data analysis.

### JSON Export

Structured data for programmatic use, including GPS coordinates, hashes, and full tag dictionaries.

---

## 📁 Thumbnails

If a file contains an embedded thumbnail (common in JPEGs) or supports thumbnail generation (via Pillow), Catify saves it as `{original_name}_thumb.jpg` inside the directory specified by `--thumbs` (default: `catify_thumbs`).

| Format group | Thumbnail behavior |
|---|---|
| JPEG/TIFF | Extracted from embedded EXIF thumbnail |
| PNG/WEBP/BMP/GIF/HEIC/HEIF | Generated via Pillow (resized to 160×160) |
| RAW | Not supported |
| Video | Not supported |

---

## ⚠️ Requirements Summary

| Requirement | Notes |
|---|---|
| Python 3.7+ | — |
| `exifread` | Required |
| `rich` | Required |
| `Pillow` | Optional, for common image formats |
| `rawpy` | Optional, for RAW formats |
| `pymediainfo` + MediaInfo | Optional, for video formats |

---

## 🐾 Author

**@tc4dy** 

The previous version (V1) has been further developed to offer improved formatting, broader format support, and more comprehensive metadata extraction.
