import os
from Classifier.src.utils.classifier_utils import classify_image_with_mask
from Classifier.src.smoothing import smooth_predictions
from Classifier.src.postprocess import save_analysis_outputs
from Classifier.src.stats import *
from Classifier.src.config import CLASS_NAMES, COLORS, DEFAULT_CONFIG
from Classifier.src.utils.convert import convert_to_float, to_serializable
from tensorflow.keras.models import load_model

from Classifier.src.config import CLASS_MAPPING
from Classifier.src.utils.classifier_utils import classify_image_with_interpolation

def load_classification_model(model_path):
    """Load Keras model"""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    return load_model(model_path)


def compute_global_context(pred_probs):
    """obsolete"""
    global_prob = np.mean(pred_probs, axis=0)
    global_prob /= np.sum(global_prob)
    return global_prob


def get_analysis_mode_config(analysis_mode):
    """
    Args:
        analysis_mode: "fast" (64x64) or "detailed" (32x32 hierarchical)
    Returns:
         configuration dict
    """
    if analysis_mode == "fast":
        return {
            "tile_size": 64,
            "hierarchical_weight": 0.0,
            "class_priorities": {
                "Forest": 1.0,
                "Highway": 0.8,
                "SeaLake": 0.8
            },
            "fix_sealake": True,
            "description": "Fast 64x64"
        }
    elif analysis_mode == "detailed":
        return {
            "tile_size": 32,
            "hierarchical_weight": 0.55,
            "class_priorities": {
                "Forest": 1.0,
                "Highway": 0.8,
                "SeaLake": 0.8
            },
            "fix_sealake": True,
            "sealake_isolation_threshold": 2,
            "min_forest_prob": 0.15,
            "description": "Detailed 32x32"
        }
    else:
        return get_analysis_mode_config("detailed")


def run_analysis(image_path, model_path=None, options=None):
    """
    main entrypoint for analysis.
    handle classify + stats
    Returns (stats_dict, outputs_dict)
    """
    if options is None:
        options = {}

    cfg = {**DEFAULT_CONFIG, **options}
    analysis_mode = cfg.get("ANALYSIS_MODE", "detailed")
    mode_config = get_analysis_mode_config(analysis_mode)

    # + allow override options
    use_interpolation = cfg.get("APPLY_INTERPOLATION", False)
    use_simplified = cfg.get("USE_SIMPLIFIED_CLASSES", False)

    if "TILE_SIZE" in options:
        tile_size = options["TILE_SIZE"]
        print(f"[DEBUG] tile_size override: {tile_size}") # generalnie dla obsolete wersji gdzie mozna bylo wpisac tile-size + debugowania
    else:
        tile_size = mode_config["tile_size"]

    hierarchical_weight = cfg.get("HIERARCHICAL_WEIGHT", mode_config["hierarchical_weight"])
    class_priorities = cfg.get("CLASS_PRIORITIES", mode_config["class_priorities"])
    fix_sealake = cfg.get("FIX_SEALAKE", mode_config.get("fix_sealake", False))

    print(f"[INFO] Mode: {analysis_mode} - {mode_config['description']}")
    print(f"[INFO] Tile size: {tile_size}x{tile_size}")
    print(f"[INFO] Interpolation: {use_interpolation}")
    print(f"[INFO] Simplified classes: {use_simplified}")
    if hierarchical_weight > 0:
        print(f"[INFO] Hierarchical weight: {hierarchical_weight}")
    print(f"[INFO] priorities (t/f): {class_priorities}")
    print(f"[INFO] sealake (t/f): {fix_sealake}")

    model_path = model_path or cfg["MODEL_PATH"]
    model = load_classification_model(model_path)

    mask = cfg.get('mask', None)

    if use_interpolation:
        print("[INFO] Detailed")
        results = classify_image_with_interpolation(
            image_path=image_path,
            model=model,
            img_size=cfg["IMG_SIZE"],
            tile_size=tile_size,
            class_names=CLASS_NAMES,
            mask=mask,
            use_interpolation=True,
            use_simplified=use_simplified,
            class_mapping=CLASS_MAPPING if use_simplified else None,
            hierarchical_weight=hierarchical_weight,  # NEW: przekaż to!
            class_priorities=class_priorities  # NEW: i to!
        )
        active_class_names = results.get("active_class_names", CLASS_NAMES)
        active_colors = {cls: COLORS[cls] for cls in active_class_names if cls in COLORS}
    else:
        print("[INFO] Using hierarchical classification")
        results = classify_image_with_mask(
            image_path=image_path,
            model=model,
            img_size=cfg["IMG_SIZE"],
            tile_size=tile_size,
            class_names=CLASS_NAMES,
            mask=mask,
            hierarchical_weight=hierarchical_weight,
            class_priorities=class_priorities,
            fix_sealake=fix_sealake,
            sealake_isolation_threshold=mode_config.get("sealake_isolation_threshold", 2),
            min_forest_prob=mode_config.get("min_forest_prob", 0.15)
        )
        active_class_names = CLASS_NAMES
        active_colors = COLORS

    pred_grid = results["pred_grid"]
    conf_grid = results["conf_grid"]
    original = results["original"]
    sealake_changes = results.get("sealake_changes", [])

    if use_interpolation and "full_res_class_indices" in results:
        full_res_indices = results["full_res_class_indices"]
        full_res_confidence = results["full_res_confidence"]
        use_full_res = True
    else:
        use_full_res = False

    global_prob = compute_global_context(results["pred_probs"])
    results["global_prob"] = global_prob

    change_log = []
    if cfg.get("APPLY_SMOOTHING", True) and not use_interpolation:
        print(f"[INFO] Applying spatial smoothing")
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
        print(f"[INFO] Smoothing changed {len(change_log)} tiles")

    h, w, _ = original.shape
    # fix: + pred_grid dimensions

    use_full_res_mask = (use_interpolation and
                         "full_res_class_indices" in results and
                         "full_res_confidence" in results)

    if use_full_res_mask:
        print("[INFO] full-resolution classification mask")
        full_res_indices = results["full_res_class_indices"]
        full_res_confidence = results["full_res_confidence"]

        classification_mask = np.zeros((h, w, 3), dtype=np.uint8)
        valid_tiles_mask = np.ones((h, w), dtype=np.uint8) * 255  

        for i, cls_name in enumerate(active_class_names):
            if cls_name not in active_colors:
                continue
            color = active_colors[cls_name]
            class_pixels = (full_res_indices == i)
            classification_mask[class_pixels] = color

        cfg['full_res_indices'] = full_res_indices
        cfg['full_res_confidence'] = full_res_confidence
    else:
        print("[INFO] tile-based classification mask")
        tile_size_actual = h // pred_grid.shape[0] if pred_grid.shape[0] > 0 else tile_size
        classification_mask = np.zeros((h, w, 3), dtype=np.uint8)
        valid_tiles_mask = np.zeros((h, w), dtype=np.uint8)

        grid_h, grid_w = pred_grid.shape
        print(f"[DEBUG] pred_grid shape: {pred_grid.shape}, image shape: {h}x{w}, tile_size: {tile_size}")

        for yi in range(grid_h):
            for xi in range(grid_w):
                y = yi * tile_size_actual
                x = xi * tile_size_actual
                if y + tile_size_actual > h or x + tile_size_actual > w:
                    continue

                cls = pred_grid[yi, xi]
                if cls == -1 or cls >= len(active_class_names):
                    continue

                color = active_colors[active_class_names[cls]]
                classification_mask[y:y + tile_size_actual, x:x + tile_size_actual] = color
                valid_tiles_mask[y:y + tile_size_actual, x:x + tile_size_actual] = 255

    print(f"[INFO] Valid pixels: {np.sum(valid_tiles_mask > 0)}")
    print(f"[INFO] Masked pixels: {np.sum(valid_tiles_mask == 0)}")

    zoom = cfg.get('zoom')
    bounds = cfg.get('bounds')
    raw_stats = {
        "areas_sq_km": compute_class_areas(
            classification_mask, active_class_names,
            valid_mask=valid_tiles_mask,
            zoom=zoom,
            bounds=bounds
        ),
        "areas_pct": compute_class_areas_percentage(
            classification_mask, active_class_names,
            valid_mask=valid_tiles_mask
        ),
        "density_default": compute_density(classification_mask, active_class_names),
        "fragmentation_index": compute_fragmentation_index(classification_mask, active_class_names),
        "adjacency_proportions": compute_boundary_analysis(classification_mask, active_class_names),
    }
    stats = convert_to_float(raw_stats)

    cfg['valid_mask_computed'] = valid_tiles_mask
    cfg['analysis_mode'] = analysis_mode
    cfg['tile_size'] = tile_size
    cfg['hierarchical_weight'] = hierarchical_weight
    cfg['class_priorities'] = class_priorities
    cfg['fix_sealake'] = fix_sealake
    cfg['sealake_fixes'] = len(sealake_changes)
    cfg['use_interpolation'] = use_interpolation
    cfg['use_simplified'] = use_simplified
    cfg['active_class_names'] = active_class_names

    outputs = save_analysis_outputs(
        classification_results=results,
        stats=stats,
        change_log=change_log,
        config=cfg,
        image_path=image_path,
        model_path=model_path
    )

    if sealake_changes:
        outputs['sealake_changes'] = sealake_changes

    print(f"[INFO] Analysis complete!")
    if use_full_res_mask:
        print(f"[INFO] - Mean confidence: {np.mean(cfg['full_res_confidence']):.4f}")
    else:
        print(f"[INFO] - Mean confidence: {np.mean(conf_grid[pred_grid != -1]):.4f}")
    print(f"[INFO] - Smoothing changes: {len(change_log)}")
    print(f"[INFO] - SeaLake fixes: {len(sealake_changes)}")

    return to_serializable(stats), to_serializable(outputs)