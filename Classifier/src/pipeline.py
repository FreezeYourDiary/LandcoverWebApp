import os
from Classifier.src.classifier import *
from Classifier.src.smoothing import smooth_predictions
from Classifier.src.postprocess import save_analysis_outputs  # Renamed import
from Classifier.src.stats import *
from Classifier.src.config import CLASS_NAMES, DEFAULT_CONFIG
from Classifier.src.utils.convert import convert_to_float, to_serializable
from Classifier.src.utils.classifier_utils import classify_image_with_mask


def run_analysis(image_path, model_path=None, options=None):
    """
    main entrypoint for analysis.
    handle classify + stats
    Returns (stats_dict, outputs_dict)
    """
    if options is None:
        options = {}
    cfg = {**DEFAULT_CONFIG, **options}

    model_path = model_path or cfg["MODEL_PATH"]
    model = load_classification_model(model_path)

    mask = cfg.get('mask', None)

    if mask is not None:
        print("[INFO] Using mask-aware classification")
        try:
            from Classifier.src.utils.classifier_utils import classify_image_with_mask
            results = classify_image_with_mask(
                image_path=image_path,
                model=model,
                img_size=cfg["IMG_SIZE"],
                tile_size=cfg["TILE_SIZE"],
                class_names=CLASS_NAMES,
                mask=mask
            )
        except ImportError:
            print("[WARN] classifier_utils not found, using standard classification")
            results = classify_image(
                image_path=image_path,
                model=model,
                img_size=cfg["IMG_SIZE"],
                tile_size=cfg["TILE_SIZE"],
                class_names=CLASS_NAMES
            )
    else:
        results = classify_image(
            image_path=image_path,
            model=model,
            img_size=cfg["IMG_SIZE"],
            tile_size=cfg["TILE_SIZE"],
            class_names=CLASS_NAMES
        )

    pred_grid = results["pred_grid"]
    conf_grid = results["conf_grid"]
    original = results["original"]

    # globalny kontekst todo to be updated with new network
    global_prob = compute_global_context(results["pred_probs"])
    results["global_prob"] = global_prob

    if cfg.get("APPLY_SMOOTHING", True):
        valid_mask = pred_grid != -1
        pred_grid, change_log = smooth_predictions(
            pred_grid,
            conf_grid,
            global_prob,
            confidence_thresh=cfg["CONF_THRESH"],
            neighborhood=cfg["NEIGHBORHOOD"],
            valid_mask=valid_mask
        )
        results["pred_grid"] = pred_grid
    else:
        change_log = []

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
                continue

            color = COLORS[CLASS_NAMES[cls]]
            classification_mask[y:y + tile_size, x:x + tile_size] = color
            valid_tiles_mask[y:y + tile_size, x:x + tile_size] = 255
    print(f"[INFO] Valid pixels: {np.sum(valid_tiles_mask > 0)}")
    print(f"[INFO] Masked pixels: {np.sum(valid_tiles_mask == 0)}")

    zoom = cfg.get('zoom')
    bounds = cfg.get('bounds')  # zoom bounds for stats calc ***

    raw_stats = {
        "areas_sq_km": compute_class_areas(
            classification_mask, CLASS_NAMES,
            valid_mask=valid_tiles_mask,
            zoom=zoom,
            bounds=bounds
        ),
        "areas_pct": compute_class_areas_percentage(
            classification_mask, CLASS_NAMES,
            valid_mask=valid_tiles_mask
        ),
        "density_default": compute_density(classification_mask, CLASS_NAMES),
        "fragmentation_index": compute_fragmentation_index(classification_mask, CLASS_NAMES),
        "adjacency_proportions": compute_boundary_analysis(classification_mask, CLASS_NAMES),
    }
    stats = convert_to_float(raw_stats)

    cfg['valid_mask_computed'] = valid_tiles_mask

    outputs = save_analysis_outputs(
        classification_results=results,
        stats=stats,
        change_log=change_log,
        config=cfg,
        image_path=image_path,
        model_path=model_path
    )

    return to_serializable(stats), to_serializable(outputs)

