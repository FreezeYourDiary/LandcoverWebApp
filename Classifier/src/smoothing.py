# smoothing.py

import numpy as np
from config import CLASS_NAMES, CLASS_PRIORITY


def smooth_predictions(pred_grid, conf_grid, global_prob, confidence_thresh, neighborhood,
                       class_priority=CLASS_PRIORITY):
    smoothed = pred_grid.copy()
    h, w = pred_grid.shape
    r = neighborhood // 2
    change_log = []

    for y in range(h):
        for x in range(w):
            cls = pred_grid[y, x]
            conf = conf_grid[y, x]
            if conf >= confidence_thresh:
                continue

            y1, y2 = max(0, y - r), min(h, y + r + 1)
            x1, x2 = max(0, x - r), min(w, x + r + 1)
            window = pred_grid[y1:y2, x1:x2].flatten()

            # debug check for empty window (>? r >= 0)
            if window.size == 0:
                continue

            majority_class = np.bincount(window).argmax()

            cls_name = CLASS_NAMES[cls]
            neigh_name = CLASS_NAMES[majority_class]
            local_score = conf * global_prob[cls] * class_priority.get(cls_name, 1.0)
            neigh_score = global_prob[majority_class] * class_priority.get(neigh_name, 1.0)

            if neigh_score > local_score:
                smoothed[y, x] = majority_class
                change_log.append({
                    "tile": (y, x),
                    "from": cls_name,
                    "to": neigh_name,
                    # "confidence": conf,
                    # "local_score": local_score,
                    # "neigh_score": neigh_score,
                    "confidence": float(conf),
                    "local_score": float(local_score),
                    "neigh_score": float(neigh_score)
                })

    print(f"[SMOOTHING] Changed {len(change_log)} tiles")
    return smoothed, change_log