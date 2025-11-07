''' ADJUSTED DLA CROPPED CLASSIFIER'''
# TODO Wstepne prawdopodobienstwo, ndvi indexes
import cv2
import numpy as np
from keras.src.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array


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


def classify_image_with_mask(image_path, model, img_size, tile_size, class_names, mask=None):
    """
    classify_image +++ mask
        mask: Optional binary mask (0/255) to skip masked areas
    Returns:
        Dict with pred_grid, conf_grid, pred_probs, original, metadata
    """
    print(f"[INFO] Loading image: {image_path}")
    original = cv2.imread(image_path)
    if original is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    h, w, _ = original.shape
    print(f"[INFO] Image size: {w}x{h}")

    tiles_y = (h + tile_size - 1) // tile_size
    tiles_x = (w + tile_size - 1) // tile_size
    total_tiles = tiles_y * tiles_x

    pred_grid = np.zeros((tiles_y, tiles_x), dtype=int)
    conf_grid = np.zeros((tiles_y, tiles_x), dtype=float)
    pred_probs_list = []

    skipped_tiles = 0
    processed_tiles = 0

    print(f"[INFO] Processing {tiles_y}x{tiles_x} = {total_tiles} tiles...")

    for yi, y in enumerate(range(0, h, tile_size)):
        for xi, x in enumerate(range(0, w, tile_size)):
            # Extract patch
            y_end = min(y + tile_size, h)
            x_end = min(x + tile_size, w)
            patch = original[y:y_end, x:x_end]

            # Check if patch is valid
            if patch.shape[0] == 0 or patch.shape[1] == 0:
                continue

            # Extract corresponding mask patch if provided
            if mask is not None:
                mask_patch = mask[y:y_end, x:x_end]

                # Skip if mostly masked
                if check_masked(patch, mask_patch, threshold=0.3):
                    pred_grid[yi, xi] = -1  # Mark as skipped
                    conf_grid[yi, xi] = 0.0
                    skipped_tiles += 1
                    continue

            # Pad if needed (edges)
            if patch.shape[0] < tile_size or patch.shape[1] < tile_size:
                patch = pad_incomplete_patch(patch, (tile_size, tile_size), method='reflect')


            patch_resized = cv2.resize(patch, (img_size, img_size))
            patch_rgb = cv2.cvtColor(patch_resized, cv2.COLOR_BGR2RGB)

            # BASELINE
            # arr = img_to_array(patch_rgb) / 255.0
            # arr = np.expand_dims(arr, axis=0)


            # MOBILENET
            # TODO IS THIS /255 as
            #  Zrobic handling dla kazdej modeli osobno well
            arr = img_to_array(patch_rgb)
            arr = preprocess_input(arr)
            arr = np.expand_dims(arr, axis=0)

            pred = model.predict(arr, verbose=0)[0]
            pred_class = np.argmax(pred)
            conf = np.max(pred)

            pred_grid[yi, xi] = pred_class
            conf_grid[yi, xi] = conf
            pred_probs_list.append(pred)
            processed_tiles += 1

    print(f"[INFO] Processed: {processed_tiles}, Skipped: {skipped_tiles}")

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
    }

    return {
        "pred_grid": pred_grid,
        "conf_grid": conf_grid,
        "pred_probs": pred_probs,
        "original": original,
        "metadata": metadata
    }