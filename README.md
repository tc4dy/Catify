![Catify](catify.jpg)

# 🐱 Catify – Professional EXIF Metadata Tool

**Catify** is a powerful command-line tool to extract, analyze, and report EXIF metadata from image files. It supports JPEG and TIFF formats, detects duplicate files via SHA256, extracts GPS coordinates with direct map links, saves embedded thumbnails, and generates beautiful terminal output or export reports in CSV, JSON, or HTML.

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Dependencies](https://img.shields.io/badge/deps-exifread%2C%20rich-orange)]()

---

## ✨ Features

- 🖼️ **Supported formats**
Pictures: JPG, JPEG, TIFF, TIF, PNG, WEBP, HEIC, HEIF, BMP, GIF

RAW: RAW, CR2, CR3, NEF, ARW, DNG

Video: MP4, MOV, AVI, MKV, WEBM, MTS, M2TS

- 📸 **Full EXIF data** – Camera make, model, exposure, ISO, datetime, etc.
- 🌍 **GPS extraction** – Converts DMS to decimal, provides Google Maps & OpenStreetMap links
- 🔍 **Duplicate detection** – SHA256 hash comparison
- 🖼️ **Thumbnail extraction** – Saves embedded thumbnails to a separate directory
- 📊 **Rich terminal output** – Colorful tables with progress bar (using `rich`)
- 📄 **Multiple export formats** – CSV, JSON, HTML (viewable in any browser)
- 🚀 **Recursive scanning** – Process entire folder trees
- 🧹 **Clean and fast** – Handles large files efficiently

---

## 📦 Installation

### 1. Clone or download the script

```bash
git clone https://github.com/yourusername/catify.git
cd catify
```

2. Install dependencies

```bash
pip install exifread rich
```

3. Run the tool

```bash
python catify.py --help
```

---

🚀 Usage

```bash
python catify.py -i <INPUT> [OPTIONS]
```

Required argument

Argument Description
-i, --input PATH Path to a single image file or a directory

Optional arguments

Option Description
-r, --recursive Scan subdirectories recursively
--csv FILE Export report to CSV format
--json FILE Export report to JSON format
--html FILE Export report to HTML format
--thumbs DIR Directory to save thumbnails (default: catify_thumbs)
-v, --verbose Print each file name while processing
--version Show version information

---

📖 Examples

Analyze a single image

```bash
python catify.py -i vacation.jpg
```

Scan a folder (including subfolders) and generate HTML report

```bash
python catify.py -i ./photos -r --html report.html
```

Full export: CSV, JSON, HTML, with thumbnails and verbose output

```bash
python catify.py -i ./images -r --csv metadata.csv --json exif.json --html report.html --thumbs my_thumbs -v
```

Only show terminal output (no exports)

```bash
python catify.py -i DSC_001.jpg
```

---

📊 Output Examples

Terminal (Rich Table)

```
  /\_____/\
 /  o   o  \
( ==  ^  == )
 )  C A T  (
(  I F Y   )
 \ ExFin  /
  '-------'
Catify v2.0.0 — Professional EXIF Metadata Tool

5 files found, processing…

┌───────────────────────────── Summary ──────────────────────────────┐
│  Total files   5                                                   │
│  EXIF OK       4                                                   │
│  No EXIF       0                                                   │
│  Error         1                                                   │
│  Duplicate     2                                                   │
│  With GPS      1                                                   │
│  Thumbnail     3                                                   │
└────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  photo.jpg                               [green]OK[/green] [magenta]DUPLICATE[/magenta]   │
│  /home/user/photos/photo.jpg                                       │
│  Size: 2.3 MB  Date: 2024-01-15 14:32:10                           │
│  SHA256: a1b2c3d4e5f6…                                             │
│  Same file: /backup/photo.jpg                                      │
│  GPS: 41.0082, 28.9784  Google Maps  OSM                           │
│  Thumbnail: catify_thumbs/photo_thumb.jpg                          │
│                                                                     │
│  ┌──────────────────────────── EXIF ─────────────────────────────┐ │
│  │ Tag                    Value                                  │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │ Image Make             Canon                                  │ │
│  │ Image Model            EOS 5D                                 │ │
│  │ EXIF ExposureTime      1/125                                  │ │
│  │ EXIF FNumber           2.8                                    │ │
│  │ EXIF ISO               100                                    │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

HTML Report

Open the generated .html file in any browser. It shows:

· Summary statistics cards
· Each file with tags, GPS links, thumbnails, and EXIF table
· Dark theme, responsive design

CSV Export

All EXIF tags become columns. Perfect for Excel or data analysis.

JSON Export

Structured data for programmatic use.

---

📁 Thumbnails

If an image contains an embedded thumbnail (common in JPEGs), Catify saves it as {original_name}_thumb.jpg inside the directory specified by --thumbs (default: catify_thumbs). Thumbnails are not generated – they are extracted from the original file.

---

⚠️ Requirements

· Python 3.7 or higher
· exifread – EXIF parsing
· rich – Terminal formatting

Install both with:

```bash
pip install exifread rich
```
🐾 Author

@tc4dy | Claude provides debugging and output support. 🙏
