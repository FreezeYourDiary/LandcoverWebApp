# Classifier/src/utils/wojewodztwo_processor.py
import json
import os
import cv2
import numpy as np
from shapely.geometry import shape, MultiPolygon, Polygon
import geopandas as gpd
from shapely.geometry import shape
import hashlib
import unicodedata
import re


def unify_lang_file(filename):
    normalized = unicodedata.normalize('NFKD', filename)
    ascii_name = normalized.encode('ascii', 'ignore').decode('ascii')
    ascii_name = re.sub(r'[^\w\s-]', '', ascii_name)
    ascii_name = re.sub(r'[-\s]+', '_', ascii_name)
    return ascii_name.lower()


def load_wojewodztwa_geojson(geojson_path):
    """
    loadgeojson, get bounds (shape)
    """
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    wojewodztwa = []
    for feature in data['features']:
        props = feature['properties']
        geom = feature['geometry']

        shape_geom = shape(geom)
        bounds = shape_geom.bounds  # (minx, miny, maxx, maxy)

        wojewodztwa.append({
            'id': props['id'],
            'nazwa': props['nazwa'],
            'geometry': geom,
            'bounds': list(bounds),
            'shapely_geom': shape_geom
        })

    return wojewodztwa


def create_mask_from_geometry(image_shape, geometry, bounds, zoom):
    """
    Args:
        image_shape: (height, width) of the image, shape geometry
        [minx, miny, maxx, maxy] in lat/lon, zoom
    Returns:
        Binary mask (0/255) --- 255 = inside województwo
    """
    h, w = image_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    minx, miny, maxx, maxy = bounds
    def lonlat_to_pixel(lon, lat):
        x_pct = (lon - minx) / (maxx - minx)
        y_pct = (maxy - lat) / (maxy - miny)  # Flip Y
        return int(x_pct * w), int(y_pct * h)
    if isinstance(geometry, MultiPolygon):
        polygons = list(geometry.geoms)
    elif isinstance(geometry, Polygon):
        polygons = [geometry]
    else:
        return mask

    for polygon in polygons:
        exterior_coords = list(polygon.exterior.coords)
        pts = np.array([lonlat_to_pixel(lon, lat) for lon, lat in exterior_coords], dtype=np.int32)
        cv2.fillPoly(mask, [pts], 255)

        # holesy
        for interior in polygon.interiors:
            interior_coords = list(interior.coords)
            pts = np.array([lonlat_to_pixel(lon, lat) for lon, lat in interior_coords], dtype=np.int32)
            cv2.fillPoly(mask, [pts], 0)

    return mask


def crop_image_by_mask(image_path, mask, output_path):
    """
        crop by binary mask
    Args:
        image_path: Path to input image
        mask: Binary mask (0/255)
        output_path: Path to save cropped image

    Returns:
        (output_path, crop_mask, crop_offset)
        crop_offset: (x_offset, y_offset) for coordinate translation
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No valid contours found in mask")

    x, y, w, h = cv2.boundingRect(np.concatenate(contours))
    cropped_img = img[y:y + h, x:x + w]
    cropped_mask = mask[y:y + h, x:x + w]

    # riginal for display
    # mask for classification todo skip tense?
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, cropped_img)
    mask_output_path = output_path.replace('.jpg', '_mask.png')
    cv2.imwrite(mask_output_path, cropped_mask)

    return output_path, cropped_mask, (x, y)


def make_wojewodztwo_cache_key(wojewodztwo_id, model_path, params):
    """
    woj cache
    """
    data = {
        'wojewodztwo_id': wojewodztwo_id,
        'model': os.path.basename(model_path),
        'params': params
    }
    key_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(key_str.encode()).hexdigest()[:32]


def calculate_geospat(geometry):
    """

    """
    try:
        # Create GeoDataFrame with WGS84 (EPSG:4326)
        gdf = gpd.GeoDataFrame([1], geometry=[geometry], crs="EPSG:4326")
        # Project to metric CRS for Poland (EPSG:2180 - PUWG 1992)
        gdf_projected = gdf.to_crs("EPSG:2180")
        area_m2 = gdf_projected.geometry.area.values[0]
        area_km2 = area_m2 / 1_000_000

        return area_km2
    except ImportError:
        bounds = geometry.bounds
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        # ~~ Poland's latitude (~52°)
        km_per_degree = 111
        area_km2 = width * height * (km_per_degree ** 2) * np.cos(np.radians(52))
        return area_km2