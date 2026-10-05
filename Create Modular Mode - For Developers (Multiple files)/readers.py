from pathlib import Path
from datetime import datetime
import exifread

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
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
                from extractors import extract_gps_from_pillow
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