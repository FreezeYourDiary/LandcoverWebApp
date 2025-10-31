# postprocess.py
import os
import cv2
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from datetime import datetime
from config import CLASS_NAMES, COLORS, DEFAULT_CONFIG

def save_analysis_outputs(classification_results, stats, change_log, config, image_path, model_path):
    """
    Generates the final classification mask, visualizations,
    and saves JSON files with full metadata and statistics.
    """
    pred_grid = classification_results["pred_grid"]
    conf_grid = classification_results["conf_grid"]
    original = classification_results["original"]
    global_prob = classification_results["global_prob"]
    class_metadata = classification_results["metadata"]
    APPLY_SMOOTHING = config.get("APPLY_SMOOTHING", DEFAULT_CONFIG["APPLY_SMOOTHING"])
    CONF_THRESH = config.get("CONF_THRESH", DEFAULT_CONFIG["CONF_THRESH"])
    NEIGHBORHOOD = config.get("NEIGHBORHOOD", DEFAULT_CONFIG["NEIGHBORHOOD"])
    # model_name = os.path.splitext(os.path.basename(model_path))[0]
    image_name = os.path.splitext(os.path.basename(image_path))[0]

    h, w, _ = original.shape
    tile_size = h // pred_grid.shape[0] if pred_grid.shape[0] > 0 else 0  # ! Defensive check

    classification_mask = np.zeros((h, w, 3), dtype=np.uint8)
    for yi, y in enumerate(range(0, h, tile_size)):
        for xi, x in enumerate(range(0, w, tile_size)):
            if y + tile_size > h or x + tile_size > w:
                continue
            cls = pred_grid[yi, xi]
            color = COLORS[CLASS_NAMES[cls]]
            classification_mask[y:y + tile_size, x:x + tile_size] = color

    # classification_mask = np.zeros((h, w, neighbours))
    # for yi, y in enumerate(range(0, h, tile_size)):
    #     for xi, x in enumerate(range(0, w, tile_size)):
    #         if y + tile_size > h or x + tile_size > w:
    #             continue
    #         cls = pred_grid[yi, xi]
    #         color = COLORS[CLASS_NAMES[cls]]
    #         classification_mask[y:y + tile_size, x:x + tile_size] = color
    alpha = 0.8
    blended = cv2.addWeighted(original, alpha, classification_mask, 1 - alpha, 0)

    # ------- Setup output paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir_relative = config.get("OUTPUT_BASE_DIR", DEFAULT_CONFIG["OUTPUT_BASE_DIR"])
    model_name = os.path.splitext(os.path.basename(model_path))[0]

    base_dir = os.path.join(os.path.dirname(__file__), "..", output_dir_relative, model_name)

    os.makedirs(base_dir, exist_ok=True)

    fig_path = os.path.join(base_dir, f"{image_name}_{timestamp}.png")
    metadata_json_path = os.path.join(base_dir, f"{image_name}_{timestamp}_metadata.json")
    stats_json_path = os.path.join(base_dir, f"{image_name}_{timestamp}_stats.json")
    log_path = os.path.join(base_dir, f"{image_name}_{timestamp}_change_log.json")

    # +++: mask and blended image (can be commented out if only the figure is needed)
    # mask_path = os.path.join(base_dir, f"{image_name}_{timestamp}_mask.png")
    # blended_path = os.path.join(base_dir, f"{image_name}_{timestamp}_blended.png")

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
        **class_metadata,  # classifier metadata : sizes, tile counts, mean conf
        "apply_smoothing": APPLY_SMOOTHING,
        "confidence_threshold": CONF_THRESH,
        "neighborhood": NEIGHBORHOOD,
        "global_context_probabilities": {
            CLASS_NAMES[i]: float(global_prob[i]) for i in range(len(CLASS_NAMES))
        },
        "smoothing_changes": len(change_log),
        "output_files": {
            "fig": fig_path,
            "metadata_json": metadata_json_path,
            "stats_json": stats_json_path,
            "change_log": log_path
        }
    }
    with open(metadata_json_path, "w") as f:
        json.dump(metadata, f, indent=4)

    plt.figure(figsize=(16, 8))

    plt.subplot(1, 3, 1)
    plt.imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))
    plt.axis("off");
    plt.title("Original")
    plt.subplot(1, 3, 2)
    plt.imshow(cv2.cvtColor(classification_mask, cv2.COLOR_BGR2RGB))
    plt.axis("off");
    plt.title("Mask")
    plt.subplot(1, 3, 3)
    plt.imshow(cv2.cvtColor(blended, cv2.COLOR_BGR2RGB))
    plt.axis("off");
    plt.title("Blended")

    patches = [mpatches.Patch(color=np.array(rgb[::-1]) / 255.0, label=cls)
               for cls, rgb in COLORS.items()]
    plt.figlegend(handles=patches, loc="lower center", ncol=5)
    plt.tight_layout(rect=[0, 0.1, 1, 1])
    plt.savefig(fig_path)
    # plt.show()
    plt.close()

    print(f"results in {base_dir}")

    return {
        "fig": fig_path,
        "metadata_json": metadata_json_path,
        "stats_json": stats_json_path,
        "mask": classification_mask
    }