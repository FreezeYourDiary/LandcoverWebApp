import os
from Classifier.src.classifier import *
from Classifier.src.smoothing import smooth_predictions
from Classifier.src.postprocess import save_analysis_outputs  # Renamed import
from Classifier.src.stats import *
from Classifier.src.config import CLASS_NAMES, DEFAULT_CONFIG
from Classifier.src.utils.convert import convert_to_float, to_serializable


def run_analysis(image_path, model_path=None, options=None):
    """
    main entrypoint for analysis.
    handle classify + stats
    Returns (stats_dict, outputs_dict)
    """
    # merging
    if options is None:
        options = {}
    cfg = {**DEFAULT_CONFIG, **options}  # params to override defaults

    model_path = model_path or cfg["MODEL_PATH"]
    model = load_classification_model(model_path)
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
        pred_grid, change_log = smooth_predictions(
            pred_grid,
            conf_grid,
            global_prob,
            confidence_thresh=cfg["CONF_THRESH"],
            neighborhood=cfg["NEIGHBORHOOD"]
        )
        results["pred_grid"] = pred_grid
    else:
        change_log = []

    # Stats na końcowej siatce predykcji
    h, w, _ = original.shape
    tile_size = h // pred_grid.shape[0] if pred_grid.shape[0] > 0 else 0
    classification_mask = np.zeros((h, w, 3), dtype=np.uint8)
    for yi, y in enumerate(range(0, h, tile_size)):
        for xi, x in enumerate(range(0, w, tile_size)):
            if y + tile_size > h or x + tile_size > w:
                continue
            cls = pred_grid[yi, xi]
            color = COLORS[CLASS_NAMES[cls]]
            classification_mask[y:y + tile_size, x:x + tile_size] = color

    raw_stats = {
        "areas_sq_km": compute_class_areas(classification_mask, CLASS_NAMES),
        "areas_pct": compute_class_areas_percentage(classification_mask, CLASS_NAMES),
        "density_default": compute_density(classification_mask, CLASS_NAMES),
        "fragmentation_index": compute_fragmentation_index(classification_mask, CLASS_NAMES),
        "adjacency_proportions": compute_boundary_analysis(classification_mask, CLASS_NAMES),
    }
    stats = convert_to_float(raw_stats)

    outputs = save_analysis_outputs(
        classification_results=results,
        stats=stats,
        change_log=change_log,
        config=cfg,
        image_path=image_path,
        model_path=model_path
    )

    return to_serializable(stats), to_serializable(outputs)

