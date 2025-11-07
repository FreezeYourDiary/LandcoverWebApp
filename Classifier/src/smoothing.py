# smoothing.py

import numpy as np
from Classifier.src.config import CLASS_NAMES, CLASS_PRIORITY


def smooth_predictions(pred_grid, conf_grid, global_prob, confidence_thresh, neighborhood,
                       class_priority=CLASS_PRIORITY, valid_mask=None):
    smoothed = pred_grid.copy()
    h, w = pred_grid.shape
    r = neighborhood // 2
    change_log = []

    # +valid mask if need
    if valid_mask is None:
        valid_mask = pred_grid != -1

    for y in range(h):
        for x in range(w):
            if not valid_mask[y, x] or pred_grid[y, x] == -1:
                continue

            cls = pred_grid[y, x]
            conf = conf_grid[y, x]
            if conf >= confidence_thresh:
                continue

            y1, y2 = max(0, y - r), min(h, y + r + 1)
            x1, x2 = max(0, x - r), min(w, x + r + 1)
            window = pred_grid[y1:y2, x1:x2].flatten()
            if window.size == 0:
                continue
            valid_window = window[window >= 0]  # only non-negative class indices

            # +1 valid sasiad minimum
            if valid_window.size == 0:
                continue

            majority_class = np.bincount(valid_window).argmax()

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
                    "confidence": float(conf),
                    "local_score": float(local_score),
                    "neigh_score": float(neigh_score)
                })

    print(f"[SMOOTHING] Changed {len(change_log)} tiles")
    return smoothed, change_log