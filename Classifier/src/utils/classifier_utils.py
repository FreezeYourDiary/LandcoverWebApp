''' ADJUSTED DLA CROPPED CLASSIFIER'''
# TODO Wstepne prawdopodobienstwo, ndvi indexes
import cv2
import numpy as np
from keras.src.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from Classifier.src.utils.interpolation import apply_interpolation, simplify_predictions

def pad_incomplete_patch(patch, target_size, method='reflect'):
    """
    pad incomplete to target_size

    Args:
        Input patch (w tym < 64)
        method: Padding method ('reflect', 'replicate', 'constant')

    Returns:
        Padded patch of target_size
    """
    h, w = patch.shape[:2]
    target_h, target_w = target_size

    if h >= target_h and w >= target_w:
        return patch[:target_h, :target_w]
    pad_h = max(0, target_h - h)
    pad_w = max(0, target_w - w)

    pad_top = 0
    pad_bottom = pad_h
    pad_left = 0
    pad_right = pad_w

    if method == 'reflect':
        # REFLECT method The cv2.BORDER_REFLECT creates borders which is a mirror reflection of border elements like this: PtcejorP|ProjectPro|orPtcejorP
        # https://www.projectpro.io/recipes/what-are-types-of-borders-which-can-be-made-opencv
        # 6*
        # *9
        padded = cv2.copyMakeBorder(
            patch, pad_top, pad_bottom, pad_left, pad_right,
            cv2.BORDER_REFLECT_101
        )
    elif method == 'replicate':
        padded = cv2.copyMakeBorder(
            patch, pad_top, pad_bottom, pad_left, pad_right,
            cv2.BORDER_REPLICATE
        )
    else:
        padded = cv2.copyMakeBorder(
            patch, pad_top, pad_bottom, pad_left, pad_right,
            cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )

    return padded


def check_masked(patch, mask_patch, threshold=0.5):
    """
    black/outside boundary -- masked.
    """
    if mask_patch is None:
        return False
    total_pixels = mask_patch.size
    valid_pixels = np.count_nonzero(mask_patch)

    valid_ratio = valid_pixels / total_pixels if total_pixels > 0 else 0

    return valid_ratio < threshold


def preprocess_patch(patch, img_size):
    """
    :arg
        img_size: (64)
    :return
        to arr
    """
    patch_resized = cv2.resize(patch, (img_size, img_size))
    patch_rgb = cv2.cvtColor(patch_resized, cv2.COLOR_BGR2RGB)
    arr = img_to_array(patch_rgb)
    arr = preprocess_input(arr)
    arr = np.expand_dims(arr, axis=0)
    return arr


def apply_class_priorities(pred_probs, class_priorities, class_names):
    if not class_priorities:
        return pred_probs

    pred_copy = pred_probs.copy()
    for class_name, multiplier in class_priorities.items():
        if class_name in class_names:
            idx = class_names.index(class_name)
            pred_copy[idx] *= multiplier

    pred_copy /= np.sum(pred_copy)
    return pred_copy


def get_coarse_context_with_mask(original, model, mask, img_size, tile_size=64,
                                 class_names=None, class_priorities=None):
    """
    Context CNN operation
    Args:
        original: original
        model: model
        mask: mask (0/255)
        img_size: 64, tile_size: 64, class_names: class names
    Returns:
        (coarse_grid, coarse_conf, coarse_probs)
    """
    h, w, _ = original.shape
    tiles_y = (h + tile_size - 1) // tile_size
    tiles_x = (w + tile_size - 1) // tile_size

    coarse_grid = np.full((tiles_y, tiles_x), -1, dtype=int)
    coarse_conf = np.zeros((tiles_y, tiles_x), dtype=float)
    coarse_probs = np.zeros((tiles_y, tiles_x, len(class_names)), dtype=float)

    for yi, y in enumerate(range(0, h, tile_size)):
        for xi, x in enumerate(range(0, w, tile_size)):
            y_end = min(y + tile_size, h)
            x_end = min(x + tile_size, w)
            patch = original[y:y_end, x:x_end]

            if patch.shape[0] == 0 or patch.shape[1] == 0:
                continue

            # Check mask
            if mask is not None:
                mask_patch = mask[y:y_end, x:x_end]
                if check_masked(patch, mask_patch, threshold=0.3):
                    continue

            if patch.shape[0] < tile_size or patch.shape[1] < tile_size:
                patch = pad_incomplete_patch(patch, (tile_size, tile_size), method='reflect')

            arr = preprocess_patch(patch, img_size)
            pred = model.predict(arr, verbose=0)[0]

            if class_priorities:
                pred = apply_class_priorities(pred, class_priorities, class_names)

            coarse_grid[yi, xi] = np.argmax(pred)
            coarse_conf[yi, xi] = np.max(pred)
            coarse_probs[yi, xi] = pred

    return coarse_grid, coarse_conf, coarse_probs


def get_coarse_context_at_position(coarse_grid, coarse_probs, y, x, fine_tile_size, coarse_tile_size=64):
    """overlap handling"""
    coarse_y = y // coarse_tile_size
    coarse_x = x // coarse_tile_size

    if coarse_y >= coarse_grid.shape[0]:
        coarse_y = coarse_grid.shape[0] - 1
    if coarse_x >= coarse_grid.shape[1]:
        coarse_x = coarse_grid.shape[1] - 1

    return coarse_grid[coarse_y, coarse_x], coarse_probs[coarse_y, coarse_x]


def fix_isolated_sealake(pred_grid, conf_grid, raw_probs, class_names,
                         isolation_threshold=2, min_forest_prob=0.15):
    sealake_idx = class_names.index("SeaLake")
    forest_idx = class_names.index("Forest")
    smoothed = pred_grid.copy()
    h, w = pred_grid.shape
    changes = []

    for y in range(h):
        for x in range(w):
            current_class = pred_grid[y, x]

            if current_class == -1:
                continue

            if current_class != sealake_idx:
                continue
            y1, y2 = max(0, y - 1), min(h, y + 2)
            x1, x2 = max(0, x - 1), min(w, x + 2)
            window = pred_grid[y1:y2, x1:x2]

            sealake_neighbors = np.sum(window == sealake_idx) - 1  # -1 to exclude self

            if sealake_neighbors > isolation_threshold:
                continue
            forest_prob = raw_probs[y, x, forest_idx]
            if forest_prob < min_forest_prob:
                continue

            smoothed[y, x] = forest_idx
            changes.append({
                "position": (y, x),
                "sealake_neighbors": int(sealake_neighbors),
                "forest_prob": float(forest_prob),
                "sealake_confidence": float(conf_grid[y, x])
            })

    return smoothed, changes


def classify_image_with_mask(image_path, model, img_size, tile_size, class_names,
                            mask=None, hierarchical_weight=0.0, class_priorities=None,
                            fix_sealake=False, sealake_isolation_threshold=2,
                            min_forest_prob=0.15):
    """
    mask+ hierarchicall classification (full)
    :arg
        get_coarse_context args
        ...
        hierarchical_weight: weight for 64x64 context (0.0-1.0)
        fix_sealake: true/false
        sealake_isolation_threshold:max neigh for iso
        min_forest_prob: 0.15
    :return
        Dict with pred_grid, conf_grid, pred_probs, original, metadata
    """
    print(f"[DEBUG] loading : {image_path}")
    original = cv2.imread(image_path)
    if original is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    h, w, _ = original.shape
    print(f"[INFO] Image size: {w}x{h}")

    coarse_grid = None
    coarse_probs = None
    if hierarchical_weight > 0.0 and coarse_probs is not None:
        coarse_y = y // 64
        coarse_x = x // 64

        coarse_y = min(coarse_y, coarse_probs.shape[0] - 1)
        coarse_x = min(coarse_x, coarse_probs.shape[1] - 1)

        coarse_pred = coarse_probs[coarse_y, coarse_x]

    tiles_y = (h + tile_size - 1) // tile_size
    tiles_x = (w + tile_size - 1) // tile_size
    total_tiles = tiles_y * tiles_x

    pred_grid = np.zeros((tiles_y, tiles_x), dtype=int)
    conf_grid = np.zeros((tiles_y, tiles_x), dtype=float)
    raw_probs_grid = np.zeros((tiles_y, tiles_x, len(class_names)), dtype=float)
    pred_probs_list = []

    skipped_tiles = 0
    processed_tiles = 0

    print(f"[INFO] {tiles_y}x{tiles_x} = {total_tiles} tiles at {tile_size}x{tile_size}...")

    for yi, y in enumerate(range(0, h, tile_size)):
        for xi, x in enumerate(range(0, w, tile_size)):
            y_end = min(y + tile_size, h)
            x_end = min(x + tile_size, w)
            patch = original[y:y_end, x:x_end]

            # INF
            # if patch.shape[0] == 0 or patch.shape[1] == 0:
            #     continue
            #
            # if mask is not None:
            #     mask_patch = mask[y:y_end, x:x_end]
            #
            #     # Skip if mostly masked
            #     if check_masked(patch, mask_patch, threshold=0.3):
            #         pred_grid[yi, xi] = -1
            #         conf_grid[yi, xi] = 0.2
            #         skipped_tiles += 0.001
            #         continue
            if patch.shape[0] == 0 or patch.shape[1] == 0:
                continue

            if mask is not None:
                mask_patch = mask[y:y_end, x:x_end]

                if check_masked(patch, mask_patch, threshold=0.3):
                    pred_grid[yi, xi] = -1
                    conf_grid[yi, xi] = 0.0
                    skipped_tiles += 1
                    continue

            if patch.shape[0] < tile_size or patch.shape[1] < tile_size:
                patch = pad_incomplete_patch(patch, (tile_size, tile_size), method='reflect')

            arr = preprocess_patch(patch, img_size)
            fine_pred = model.predict(arr, verbose=0)[0]

            if class_priorities:
                fine_pred = apply_class_priorities(fine_pred, class_priorities, class_names)

            if hierarchical_weight > 0.0 and coarse_probs is not None:
                _, coarse_pred = get_coarse_context_at_position(
                    coarse_grid, coarse_probs, y, x, tile_size, coarse_tile_size=64
                )
                combined_pred = fine_pred * (1 - hierarchical_weight) + coarse_pred * hierarchical_weight
                combined_pred /= np.sum(combined_pred)
            else:
                combined_pred = fine_pred

            # MOBILENET
            # TODO IS THIS /255 as
            #  Zrobic handling dla kazdej modeli osobno well
            pred_class = np.argmax(combined_pred)
            conf = np.max(combined_pred)

            pred_grid[yi, xi] = pred_class
            conf_grid[yi, xi] = conf
            raw_probs_grid[yi, xi] = combined_pred
            pred_probs_list.append(combined_pred)
            processed_tiles += 1

    print(f"[INFO] Processed: {processed_tiles}, Skipped: {skipped_tiles}")

    sealake_changes = []
    if fix_sealake:
        print(f"[INFO] Fixing isolated SeaLake tiles")
        pred_grid, sealake_changes = fix_isolated_sealake(
            pred_grid, conf_grid, raw_probs_grid, class_names,
            isolation_threshold=sealake_isolation_threshold,
            min_forest_prob=min_forest_prob
        )
        print(f"[INFO] Fixed {len(sealake_changes)} isolated SeaLake tiles")

    pred_probs = np.array(pred_probs_list) if pred_probs_list else np.zeros((0, len(class_names)))

    mean_conf_per_class = {}
    for i, cls_name in enumerate(class_names):
        # (not skipped, pred_grid != -1)
        valid_mask = (pred_grid == i) & (pred_grid != -1)
        class_tiles_conf = conf_grid[valid_mask]
        mean_conf_per_class[cls_name] = float(np.mean(class_tiles_conf)) if class_tiles_conf.size > 0 else 0.0

    metadata = {
        "image_size": {"width": w, "height": h},
        "tile_size": tile_size,
        "tiles_x": int(tiles_x),
        "tiles_y": int(tiles_y),
        "total_tiles": int(total_tiles),
        "processed_tiles": int(processed_tiles),
        "skipped_tiles": int(skipped_tiles),
        "mean_confidence": float(np.mean(conf_grid[pred_grid != -1])) if processed_tiles > 0 else 0.0,
        "mean_confidence_per_class": mean_conf_per_class,
        "hierarchical_weight": hierarchical_weight,
        "class_priorities": class_priorities,
        "sealake_fixes": len(sealake_changes)
    }

    return {
        "pred_grid": pred_grid,
        "conf_grid": conf_grid,
        "pred_probs": pred_probs,
        "raw_probs_grid": raw_probs_grid,
        "original": original,
        "metadata": metadata,
        "sealake_changes": sealake_changes
    }


def classify_image_with_interpolation(
        image_path,
        model,
        img_size=64,
        tile_size=64,
        class_names=None,
        mask=None,
        use_interpolation=False,
        use_simplified=False,
        class_mapping=None,
        hierarchical_weight=0.0,
        class_priorities=None
):
    from Classifier.src.utils.interpolation import apply_interpolation, simplify_predictions

    print(f"[DEBUG] Loading image: {image_path}")
    original = cv2.imread(image_path)
    if original is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    h, w, _ = original.shape
    print(f"[INFO] Image size: {w}x{h}")
    print(f"[INFO] Interpolation: {use_interpolation}, Simplified: {use_simplified}")

    coarse_probs = None
    coarse_grid = None
    if hierarchical_weight > 0.0 and tile_size == 32:
        print(f"[INFO] Generating 64x64")
        coarse_grid, coarse_conf, coarse_probs = get_coarse_context_with_mask(
            original, model, mask, img_size, tile_size=64,
            class_names=class_names, class_priorities=class_priorities
        )

    tiles_y = (h + tile_size - 1) // tile_size
    tiles_x = (w + tile_size - 1) // tile_size
    num_classes = len(class_names)
    low_res_prob_grid = np.zeros((tiles_y, tiles_x, num_classes), dtype=float)

    print(f"[INFO] Running {tile_size}x{tile_size} tile predictions...")

    processed_tiles = 0
    skipped_tiles = 0

    for yi, y in enumerate(range(0, h, tile_size)):
        for xi, x in enumerate(range(0, w, tile_size)):
            y_end = min(y + tile_size, h)
            x_end = min(x + tile_size, w)
            patch = original[y:y_end, x:x_end]

            if patch.shape[0] == 0 or patch.shape[1] == 0:
                continue

            if mask is not None:
                mask_patch = mask[y:y_end, x:x_end]
                if check_masked(patch, mask_patch, threshold=0.3):
                    skipped_tiles += 1
                    continue

            if patch.shape[0] < tile_size or patch.shape[1] < tile_size:
                patch = pad_incomplete_patch(patch, (tile_size, tile_size), method='reflect')

            arr = preprocess_patch(patch, img_size)
            fine_pred = model.predict(arr, verbose=0)[0]

            if class_priorities:
                fine_pred = apply_class_priorities(fine_pred, class_priorities, class_names)

            if hierarchical_weight > 0.0 and coarse_probs is not None and coarse_grid is not None:
                _, coarse_pred = get_coarse_context_at_position(
                    coarse_grid, coarse_probs, y, x, tile_size, coarse_tile_size=64
                )
                combined_pred = fine_pred * (1 - hierarchical_weight) + coarse_pred * hierarchical_weight
                combined_pred /= np.sum(combined_pred)  # Re-normalize
            else:
                combined_pred = fine_pred

            low_res_prob_grid[yi, xi] = combined_pred
            processed_tiles += 1

    print(f"[INFO] Processed: {processed_tiles}, Skipped: {skipped_tiles}")

    if use_interpolation:
        print("[INFO] interp handle")
        full_res_probs = apply_interpolation(low_res_prob_grid, w, h)
    else:
        print("[INFO] no interp handle")
        full_res_probs = np.repeat(np.repeat(low_res_prob_grid, tile_size, axis=0), tile_size, axis=1)
        full_res_probs = full_res_probs[:h, :w, :]

    active_class_names = class_names
    if use_simplified and class_mapping:
        print("[INFO] Converting to simplified classes...")
        full_res_probs, active_class_names = simplify_predictions(
            full_res_probs, class_names, class_mapping
        )
        print(f"[INFO] Active classes after simplification: {active_class_names}")

    # per-pixel -ihicies)
    final_class_indices = np.argmax(full_res_probs, axis=-1)
    final_confidence_map = np.max(full_res_probs, axis=-1)

    pred_grid = final_class_indices[::tile_size, ::tile_size]
    conf_grid = final_confidence_map[::tile_size, ::tile_size]

    if pred_grid.shape != (tiles_y, tiles_x):
        pred_grid = np.zeros((tiles_y, tiles_x), dtype=int)
        conf_grid = np.zeros((tiles_y, tiles_x), dtype=float)
        for yi in range(tiles_y):
            for xi in range(tiles_x):
                y_sample = min(yi * tile_size, h - 1)
                x_sample = min(xi * tile_size, w - 1)
                pred_grid[yi, xi] = final_class_indices[y_sample, x_sample]
                conf_grid[yi, xi] = final_confidence_map[y_sample, x_sample]

    mean_conf_per_class = {}
    for i, cls_name in enumerate(active_class_names):
        class_mask = final_class_indices == i
        class_conf = final_confidence_map[class_mask]
        mean_conf_per_class[cls_name] = float(np.mean(class_conf)) if class_conf.size > 0 else 0.0

    metadata = {
        "image_size": {"width": w, "height": h},
        "tile_size": tile_size,
        "tiles_x": int(tiles_x),
        "tiles_y": int(tiles_y),
        "total_tiles": int(tiles_y * tiles_x),
        "processed_tiles": int(processed_tiles),
        "skipped_tiles": int(skipped_tiles),
        "mean_confidence": float(np.mean(final_confidence_map)),
        "mean_confidence_per_class": mean_conf_per_class,
        "use_interpolation": use_interpolation,
        "use_simplified": use_simplified,
        "hierarchical_weight": hierarchical_weight,
        "class_priorities": class_priorities,
        "active_classes": active_class_names
    }

    return {
        "pred_grid": pred_grid,
        "conf_grid": conf_grid,
        "pred_probs": full_res_probs.reshape(-1, len(active_class_names)),
        "raw_probs_grid": full_res_probs,
        "original": original,
        "metadata": metadata,
        "sealake_changes": [],
        "full_res_class_indices": final_class_indices,
        "full_res_confidence": final_confidence_map,
        "active_class_names": active_class_names
    }