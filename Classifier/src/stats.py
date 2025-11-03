import numpy as np
import cv2
from scipy import ndimage as ndi
from Classifier.src.config import COLORS

def compute_class_areas(classification_mask, class_names, pixel_size_m=10):
    """Returns area per class in km²."""
    h, w, _ = classification_mask.shape
    pixel_area_km2 = (pixel_size_m ** 2) / 1e6
    areas = {}
    for i, cls in enumerate(class_names):
        color = np.array(list(COLORS[cls]))
        mask = np.all(classification_mask == color, axis=-1)
        n_pixels = np.sum(mask)
        areas[cls] = n_pixels * pixel_area_km2
    return areas


def compute_class_areas_percentage(classification_mask, class_names):
    """Returns area per class in % of whole image."""
    total_pixels = classification_mask.shape[0] * classification_mask.shape[1]
    perc = {}
    for cls in class_names:
        color = np.array(list(COLORS[cls]))
        mask = np.all(classification_mask == color, axis=-1)
        perc[cls] = (np.sum(mask) / total_pixels) * 100
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
    """Fragmentation index = number of distinct patches per class / total area."""
    frag = {}
    for cls in class_names:
        color = np.array(list(COLORS[cls]))
        mask = np.all(classification_mask == color, axis=-1)
        labeled, num_features = ndi.label(mask)
        area = np.sum(mask)
        frag[cls] = num_features / area if area > 0 else 0
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

    # 4-neighborhood adjacency
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
    """round for json"""
    def round_values(d):
        return {k: round(v, 4) if isinstance(v, (int, float)) else v for k, v in d.items()}

    clean = {
        "areas_sq_km": round_values(stats.get("areas_sq_km", {})),
        "areas_pct": round_values(stats.get("areas_pct", {})),
        "fragmentation": round_values(stats.get("fragmentation_index", {})),
        "adjacency": {
            c1: round_values(c2dict)
            for c1, c2dict in stats.get("adjacency_proportions", {}).items()
        },
        "density": round(stats.get("density_default", 0), 4),
    }
    return clean
