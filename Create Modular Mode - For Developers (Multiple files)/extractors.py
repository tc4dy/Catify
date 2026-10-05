from pathlib import Path
import exifread

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


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
    if not PILLOW_AVAILABLE:
        return ""
    try:
        img = Image.open(path)
        img.thumbnail((160, 160))
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / f"{path.stem}_thumb.jpg"
        img.convert("RGB").save(thumb_path, "JPEG")
        return str(thumb_path.resolve())
    except Exception:
        return ""