import os
import cv2
import json
import numpy as np
from datetime import datetime
from Classifier.src.config import CLASS_NAMES, COLORS, DEFAULT_CONFIG


def save_analysis_outputs(classification_results, stats, change_log, config, image_path, model_path):
    """
    Generates the final classification mask and saves metadata.
      skip masked tiles (-1) in postprocess.
    """
    pred_grid = classification_results["pred_grid"]
    conf_grid = classification_results["conf_grid"]
    original = classification_results["original"]
    global_prob = classification_results["global_prob"]
    class_metadata = classification_results["metadata"]

    APPLY_SMOOTHING = config.get("APPLY_SMOOTHING", DEFAULT_CONFIG["APPLY_SMOOTHING"])
    CONF_THRESH = config.get("CONF_THRESH", DEFAULT_CONFIG["CONF_THRESH"])
    NEIGHBORHOOD = config.get("NEIGHBORHOOD", DEFAULT_CONFIG["NEIGHBORHOOD"])

    image_name = os.path.splitext(os.path.basename(image_path))[0]

    h, w, _ = original.shape
    tile_size = h // pred_grid.shape[0] if pred_grid.shape[0] > 0 else 0

    classification_mask = np.zeros((h, w, 3), dtype=np.uint8)
    valid_tiles_mask = np.zeros((h, w), dtype=np.uint8)

    for yi, y in enumerate(range(0, h, tile_size)):
        for xi, x in enumerate(range(0, w, tile_size)):
            if y + tile_size > h or x + tile_size > w:
                continue

            cls = pred_grid[yi, xi]
            if cls == -1:
                continue  #  as black (0, 0, 0)

            color = COLORS[CLASS_NAMES[cls]]
            classification_mask[y:y + tile_size, x:x + tile_size] = color
            valid_tiles_mask[y:y + tile_size, x:x + tile_size] = 255

    alpha = 0.5
    blended = cv2.addWeighted(original, alpha, classification_mask, 1 - alpha, 0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir_relative = config.get("OUTPUT_BASE_DIR", DEFAULT_CONFIG["OUTPUT_BASE_DIR"])
    model_name = os.path.splitext(os.path.basename(model_path))[0]
    base_dir = os.path.join(os.path.dirname(__file__), "..", output_dir_relative, model_name)
    os.makedirs(base_dir, exist_ok=True)

    mask_path = os.path.join(base_dir, f"{image_name}_{timestamp}_mask.png")
    blended_path = os.path.join(base_dir, f"{image_name}_{timestamp}_blended.png")

    cv2.imwrite(mask_path, classification_mask)
    cv2.imwrite(blended_path, blended)

    metadata_json_path = os.path.join(base_dir, f"{image_name}_{timestamp}_metadata.json")
    stats_json_path = os.path.join(base_dir, f"{image_name}_{timestamp}_stats.json")
    log_path = os.path.join(base_dir, f"{image_name}_{timestamp}_change_log.json")

    with open(log_path, "w") as f:
        json.dump(change_log, f, indent=4)
    with open(stats_json_path, "w") as f:
        json.dump(stats, f, indent=4)

    metadata = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "image_name": image_name,
        "image_path": image_path,
        "model_name": model_name,
        "model_path": model_path,
        **class_metadata,
        "apply_smoothing": APPLY_SMOOTHING,
        "confidence_threshold": CONF_THRESH,
        "neighborhood": NEIGHBORHOOD,
        "global_context_probabilities": {
            CLASS_NAMES[i]: float(global_prob[i]) for i in range(len(CLASS_NAMES))
        },
        "smoothing_changes": len(change_log),
        "output_files": {
            "mask": mask_path,
            "blended": blended_path,
            "metadata_json": metadata_json_path,
            "stats_json": stats_json_path,
            "change_log": log_path
        }
    }

    with open(metadata_json_path, "w") as f:
        json.dump(metadata, f, indent=4)

    print(f"[INFO] Results saved to {base_dir}")
    print(f"[INFO] Mask: {mask_path}")
    print(f"[INFO] Blended: {blended_path}")

    return {
        "mask": mask_path,
        "blended": blended_path,
        "metadata_json": metadata_json_path,
        "stats_json": stats_json_path,
        "change_log": log_path,
        "valid_mask": valid_tiles_mask
    }