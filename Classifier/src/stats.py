import numpy as np
import cv2
from scipy import ndimage as ndi
from Classifier.src.config import COLORS
import math

def meters_per_pixel_at_zoom(lat, zoom):
    """
    Args:
        lat: degrees
        zoom: Zoom level adjustments ** math
    """
    EARTH_CIRCUMFERENCE = 40075017
    meters_per_pixel_equator = EARTH_CIRCUMFERENCE / 256
    meters_per_pixel = meters_per_pixel_equator / (2 ** zoom)
    meters_per_pixel *= math.cos(math.radians(lat))

    return meters_per_pixel


def compute_class_areas(classification_mask, class_names, valid_mask=None, zoom=None, bounds=None):
    """
    Args:
        classification_mask, class_names: List of class names
        valid_mask: (255=valid, 0=masked) poza maska usuwa
        zoom, bounds: [minx, miny, maxx, maxy] bounding box

    Returns:
        Dict of {class_name: area_km2}
    """
    h, w, _ = classification_mask.shape

    if zoom is not None and bounds is not None:
        # center of lat
        center_lat = (bounds[1] + bounds[3]) / 2
        meters_per_pixel = meters_per_pixel_at_zoom(center_lat, zoom)
        pixel_area_m2 = meters_per_pixel ** 2
        pixel_area_km2 = pixel_area_m2 / 1_000_000
    else:
        # 10m/pixel
        pixel_area_km2 = (10 ** 2) / 1_000_000
        print("[WARN] No zoom/bounds provided, using rough estimate for pixel size")

    areas = {}
    for i, cls in enumerate(class_names):
        color = np.array(list(COLORS[cls]))
        mask = np.all(classification_mask == color, axis=-1)
        if valid_mask is not None:
            mask = mask & (valid_mask > 0)

        n_pixels = np.sum(mask)
        areas[cls] = n_pixels * pixel_area_km2

    return areas


def compute_class_areas_percentage(classification_mask, class_names, valid_mask=None):
    """Returns area per class in % of whole image."""

    if valid_mask is not None:
        total_valid_pixels = np.sum(valid_mask > 0)
    else:
        total_valid_pixels = classification_mask.shape[0] * classification_mask.shape[1]

    if total_valid_pixels == 0:
        return {cls: 0.0 for cls in class_names}

    perc = {}
    for cls in class_names:
        color = np.array(list(COLORS[cls]))
        class_pixels = np.all(classification_mask == color, axis=-1)

        if valid_mask is not None:
            class_pixels = class_pixels & (valid_mask > 0)

        perc[cls] = (np.sum(class_pixels) / total_valid_pixels) * 100

    return perc


def compute_density(classification_mask, class_names, target_classes=None):
    """Example: density = (sum of target_class pixels / total pixels)."""
    if target_classes is None:
        target_classes = ["Residential", "Industrial"]
    total_pixels = classification_mask.shape[0] * classification_mask.shape[1]
    mask_sum = np.zeros(classification_mask.shape[:2], dtype=bool)
    for cls in target_classes:
        color = np.array(list(COLORS[cls]))
        mask_sum |= np.all(classification_mask == color, axis=-1)
    density = np.sum(mask_sum) / total_pixels
    return density


def compute_fragmentation_index(classification_mask, class_names):
    frag = {}
    print("\n[FRAGMENTATION DEBUG]")
    for cls in class_names:
        color = np.array(list(COLORS[cls]))
        mask = np.all(classification_mask == color, axis=-1)
        labeled, num_features = ndi.label(mask)
        area = np.sum(mask)
        frag_value = num_features / area if area > 0 else 0

        print(f"{cls:20s}: {num_features:4d} patches, {area:8d} pixels → {frag_value:.8f}")
        frag[cls] = frag_value
    #     AnnualCrop : 6 patches, 24576 pixels → 0.00024414
    #     Forest : 10 patches, 65536 pixels → 0.00015259
    return frag


def compute_boundary_analysis(classification_mask, class_names):
    """Returns adjacency proportions between classes."""
    h, w, _ = classification_mask.shape
    adjacency = {cls: {cls2: 0 for cls2 in class_names} for cls in class_names}

    mask_idx = np.zeros((h, w), dtype=int)
    color_to_idx = {tuple(v): i for i, v in enumerate([COLORS[c] for c in class_names])}

    for y in range(h):
        for x in range(w):
            color = tuple(classification_mask[y, x])
            mask_idx[y, x] = color_to_idx.get(color, -1)
    for y in range(h - 1):
        for x in range(w - 1):
            c1, c2 = mask_idx[y, x], mask_idx[y, x + 1]
            c3, c4 = mask_idx[y, x], mask_idx[y + 1, x]
            if c1 != c2 and c1 >= 0 and c2 >= 0:
                adjacency[class_names[c1]][class_names[c2]] += 1
                adjacency[class_names[c2]][class_names[c1]] += 1
            if c3 != c4 and c3 >= 0 and c4 >= 0:
                adjacency[class_names[c3]][class_names[c4]] += 1
                adjacency[class_names[c4]][class_names[c3]] += 1

    # ++ adjacency by total granic
    total = sum(sum(v.values()) for v in adjacency.values())
    for c in adjacency:
        for c2 in adjacency[c]:
            adjacency[c][c2] = adjacency[c][c2] / total if total > 0 else 0

    return adjacency


def normalize_stats(stats: dict):
    """Round for json"""

    def round_values(d):
        if not isinstance(d, dict):
            return d
        return {k: round(v, 4) if isinstance(v, (int, float)) else v for k, v in d.items()}

    areas_sq_km = stats.get("areas_sq_km", {})
    areas_pct = stats.get("areas_pct", {})
    fragmentation = stats.get("fragmentation_index", {})
    adjacency = stats.get("adjacency_proportions", {})
    density = stats.get("density_default", 0)

    # upd cleaned up
    clean = {
        "areas_sq_km": round_values(areas_sq_km),
        "areas_pct": round_values(areas_pct),
        "fragmentation": round_values(fragmentation),
        "adjacency": {
            c1: round_values(c2dict) if isinstance(c2dict, dict) else {}
            for c1, c2dict in adjacency.items()
        } if adjacency else {},
        "density": round(density, 4) if isinstance(density, (int, float)) else 0,
    }

    return clean