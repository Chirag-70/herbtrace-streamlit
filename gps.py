from datetime import datetime, timezone
from io import BytesIO
from PIL import Image, ExifTags


def extract_exif_gps(uploaded_file):
    try:
        image = Image.open(BytesIO(uploaded_file.getvalue()))
        exif = image.getexif()
        gps_info = None
        for key, value in exif.items():
            if ExifTags.TAGS.get(key, key) == "GPSInfo":
                gps_info = value
                break
        if not gps_info:
            return None
        gps = {}
        for key, value in gps_info.items():
            gps[ExifTags.GPSTAGS.get(key, key)] = value
        required = {"GPSLatitude", "GPSLatitudeRef", "GPSLongitude", "GPSLongitudeRef"}
        if not required.issubset(gps):
            return None

        def convert(v):
            return float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600

        lat = convert(gps["GPSLatitude"])
        lon = convert(gps["GPSLongitude"])
        if gps["GPSLatitudeRef"] in ("S", b"S"):
            lat = -lat
        if gps["GPSLongitudeRef"] in ("W", b"W"):
            lon = -lon
        return {
            "latitude": lat,
            "longitude": lon,
            "accuracy_m": None,
            "source": "IMAGE_EXIF_GPS",
        }
    except Exception:
        return None


def normalize_browser_location(location):
    if not location or location.get("latitude") is None or location.get("longitude") is None:
        return None
    return {
        "latitude": float(location["latitude"]),
        "longitude": float(location["longitude"]),
        "accuracy_m": float(location["accuracy"]) if location.get("accuracy") is not None else None,
        "source": "BROWSER_GEOLOCATION",
    }


def capture_timestamp():
    return datetime.now(timezone.utc).isoformat()
