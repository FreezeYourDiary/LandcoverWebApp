# classifier.py
import os
import cv2
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array

# Generalnie
# TODO + SIEC segmentacyjna post (drogi/rzeki dla prawdopodobienstwa > ...)
#  przestrzenna pamiec

def compute_global_context(pred_probs):
    """ avg probability vector """
    # TODO weighted probabilities.
    #  global pre-pass ale na danych model widzi cały kontekst przestrzenny i kolory. ?? dataset ??
    global_prob = np.mean(pred_probs, axis=0)
    sum_prob = np.sum(global_prob)
    if sum_prob > 0:
        global_prob /= sum_prob
    return global_prob


def load_classification_model(model_path):
    """Loads the Keras model."""
    try:
        return load_model(model_path)
    except Exception as e:
        raise IOError(f"Failed to load model from {model_path}: {e}")


def classify_image(image_path, model, img_size, tile_size, class_names):
    """
    tile-based classification by dividind into tiles
    Returns: pred_grid, conf_grid, pred_probs, original_image, metadata
     ! only for test classification_mask (np.array): RGB mask of classified tiles
        ! only for test statistics (dict): percentage of each class across the image
    """
    original = cv2.imread(image_path)
    if original is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")
    # grids
    h, w, _ = original.shape
    tiles_y = (h + tile_size - 1) // tile_size
    tiles_x = (w + tile_size - 1) // tile_size
    total_tiles = tiles_y * tiles_x

    pred_grid = np.zeros((tiles_y, tiles_x), dtype=int)
    conf_grid = np.zeros((tiles_y, tiles_x), dtype=float)
    pred_probs_list = []

    # print("tile rendering")
    for yi, y in enumerate(range(0, h, tile_size)):
        for xi, x in enumerate(range(0, w, tile_size)):
            patch = original[y:y + tile_size, x:x + tile_size]
            # patches on edges
            if patch.shape[0] == 0 or patch.shape[1] == 0:
                continue

            patch_resized = cv2.resize(patch, (img_size, img_size))
            patch_rgb = cv2.cvtColor(patch_resized, cv2.COLOR_BGR2RGB)
            arr = img_to_array(patch_rgb) / 255.0
            arr = np.expand_dims(arr, axis=0)

            pred = model.predict(arr, verbose=0)[0]
            pred_class = np.argmax(pred)
            conf = np.max(pred)

            pred_grid[yi, xi] = pred_class
            conf_grid[yi, xi] = conf
            pred_probs_list.append(pred)

    pred_probs = np.array(pred_probs_list)

    mean_conf_per_class = {}
    for i, cls_name in enumerate(class_names):
        class_tiles_conf = conf_grid[pred_grid == i]
        mean_conf_per_class[cls_name] = float(np.mean(class_tiles_conf)) if class_tiles_conf.size > 0 else 0.0
    metadata = {
        "image_size": {"width": w, "height": h},
        "tile_size": tile_size,
        "tiles_x": int(tiles_x),
        "tiles_y": int(tiles_y),
        "total_tiles": int(total_tiles),
        "mean_confidence": float(np.mean(conf_grid)),
        "mean_confidence_per_class": mean_conf_per_class,
    }

    return {
        "pred_grid": pred_grid,
        "conf_grid": conf_grid,
        "pred_probs": pred_probs,
        "original": original,
        "metadata": metadata
    }