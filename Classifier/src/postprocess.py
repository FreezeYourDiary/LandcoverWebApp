import os
import cv2
import json
import numpy as np
from datetime import datetime
from Classifier.src.config import CLASS_NAMES, COLORS, DEFAULT_CONFIG
from PIL import Image
from shapely.geometry import shape


def draw_wojewodztwo_boundary(image_path, geometry, bounds, zoom, output_path=None, color=(255, 0, 0), thickness=3):
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    geom = shape(geometry)

    if geom.geom_type == 'Polygon':
        coords_list = [list(geom.exterior.coords)]
    elif geom.geom_type == 'MultiPolygon':
        coords_list = [list(poly.exterior.coords) for poly in geom.geoms]
    else:
        return image_path
    minx, miny, maxx, maxy = bounds

    def latlon_to_pixel(lon, lat):
        x_norm = (lon - minx) / (maxx - minx)
        y_norm = (maxy - lat) / (maxy - miny)
        px = int(x_norm * w)
        py = int(y_norm * h)

        return (px, py)
    for coords in coords_list:
        pixel_coords = [latlon_to_pixel(lon, lat) for lon, lat in coords]
        pts = np.array(pixel_coords, dtype=np.int32)
        cv2.polylines(img, [pts], isClosed=True, color=color, thickness=thickness)
    if output_path is None:
        output_path = image_path.replace('.jpg', '_boundary.jpg')

    cv2.imwrite(output_path, img)
    print(f"[BOUNDARY] Drawn boundary on {output_path}")

    return output_path


def create_boundary_version(cropped_image_path, geometry, bounds, zoom):
    try:
        base, ext = os.path.splitext(cropped_image_path)
        boundary_path = f"{base}_boundary{ext}"
        if os.path.exists(boundary_path):
            return boundary_path
        boundary_path = draw_wojewodztwo_boundary(
            image_path=cropped_image_path,
            geometry=geometry,
            bounds=bounds,
            zoom=zoom,
            output_path=boundary_path,
            color=(0, 0, 255),  # Red in BGR
            thickness=4
        )

        return boundary_path

    except Exception as e:
        import traceback
        traceback.print_exc()
        return cropped_image_path


def create_thumbnail(image_path, max_size=(800, 800), quality=80):
    try:
        if not os.path.exists(image_path):
            print(f"[ERROR] Image path doesn't exist: {image_path}")
            return None

        img = Image.open(image_path)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
            img = background

        original_size = img.size
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        base, ext = os.path.splitext(image_path)
        thumb_path = f"{base}_thumb.jpg"

        img.save(thumb_path, 'JPEG', quality=quality, optimize=True)

        original_mb = os.path.getsize(image_path) / (1024 * 1024)
        thumb_mb = os.path.getsize(thumb_path) / (1024 * 1024)
        reduction = 100 * (1 - thumb_mb / original_mb)

        print(f"[THUMBNAIL] {os.path.basename(image_path)}")
        print(f"  Original: {original_size[0]}x{original_size[1]} ({original_mb:.2f}MB)")
        print(f"  Thumb: {img.size[0]}x{img.size[1]} ({thumb_mb:.2f}MB) - {reduction:.1f}%")

        return thumb_path

    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to create thumbnail for {image_path}")
        print(f"[ERROR] Exception: {e}")
        traceback.print_exc()
        return None


def save_analysis_outputs(classification_results, stats, change_log, config, image_path, model_path):
    """
    Generates the final classification mask and saves metadata.
    + thumbnails dla display
    """
    pred_grid = classification_results["pred_grid"]
    conf_grid = classification_results["conf_grid"]
    original = classification_results["original"]
    global_prob = classification_results["global_prob"]
    class_metadata = classification_results["metadata"]

    # active or uproszczone
    active_class_names = config.get('active_class_names', CLASS_NAMES)
    active_colors = {cls: COLORS[cls] for cls in active_class_names if cls in COLORS}

    full_res_indices = config.get('full_res_indices', None)
    full_res_confidence = config.get('full_res_confidence', None)
    use_full_res = full_res_indices is not None

    APPLY_SMOOTHING = config.get("APPLY_SMOOTHING", DEFAULT_CONFIG["APPLY_SMOOTHING"])
    CONF_THRESH = config.get("CONF_THRESH", DEFAULT_CONFIG["CONF_THRESH"])
    NEIGHBORHOOD = config.get("NEIGHBORHOOD", DEFAULT_CONFIG["NEIGHBORHOOD"])

    image_name = os.path.splitext(os.path.basename(image_path))[0]

    h, w, _ = original.shape

    if use_full_res:
        classification_mask = np.zeros((h, w, 3), dtype=np.uint8)
        valid_tiles_mask = np.ones((h, w), dtype=np.uint8) * 255

        for i, cls_name in enumerate(active_class_names):
            if cls_name not in active_colors:
                continue
            color = active_colors[cls_name]
            class_pixels = (full_res_indices == i)
            classification_mask[class_pixels] = color
    else:
        tile_size = h // pred_grid.shape[0] if pred_grid.shape[0] > 0 else 0
        classification_mask = np.zeros((h, w, 3), dtype=np.uint8)
        valid_tiles_mask = np.zeros((h, w), dtype=np.uint8)

        grid_h, grid_w = pred_grid.shape
        print(f"[DEBUG postprocess] pred_grid shape: {pred_grid.shape}, image: {h}x{w}, tile_size: {tile_size}")

        for yi in range(grid_h):
            for xi in range(grid_w):
                y = yi * tile_size
                x = xi * tile_size

                if y + tile_size > h or x + tile_size > w:
                    continue

                cls = pred_grid[yi, xi]
                if cls == -1 or cls >= len(active_class_names):
                    continue

                color = active_colors.get(active_class_names[cls], (128, 128, 128))
                classification_mask[y:y + tile_size, x:x + tile_size] = color
                valid_tiles_mask[y:y + tile_size, x:x + tile_size] = 255

    alpha = 0.8
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

    print("[DEBUG] Generating thumbnails")
    mask_thumb = create_thumbnail(mask_path, max_size=(800, 800), quality=85)
    blended_thumb = create_thumbnail(blended_path, max_size=(800, 800), quality=85)

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
            active_class_names[i]: float(global_prob[i])
            for i in range(min(len(active_class_names), len(global_prob)))
        },
        "smoothing_changes": len(change_log),
        "active_classes": active_class_names,  # NEW: Add to metadata
        "use_interpolation": config.get('use_interpolation', False),  # NEW
        "use_simplified": config.get('use_simplified', False),  # NEW
        "output_files": {
            "mask": mask_path,
            "mask_thumb": mask_thumb,
            "blended": blended_path,
            "blended_thumb": blended_thumb,
            "metadata_json": metadata_json_path,
            "stats_json": stats_json_path,
            "change_log": log_path
        }
    }

    with open(metadata_json_path, "w") as f:
        json.dump(metadata, f, indent=4)

    active_class_names = config.get('active_class_names', CLASS_NAMES)
    residential_b64 = extract_residential_area(original, classification_mask, active_class_names)

    print(f"[INFO] Results saved to {base_dir}")
    print(f"[INFO] Mask: {mask_path}")
    print(f"[INFO] Blended: {blended_path}")
    print(f"[DEBUG] Residential extraction: {'generated' if residential_b64 else 'none'}")

    return {
        "mask": mask_path,
        "mask_thumb": mask_thumb,
        "blended": blended_path,
        "blended_thumb": blended_thumb,
        "metadata_json": metadata_json_path,
        "stats_json": stats_json_path,
        "change_log": log_path,
        "valid_mask": valid_tiles_mask,
        "residential_image": residential_b64  # NEW
    }


def extract_residential_area(original, classification_mask, class_names):
    """
    Returns base64 encoded PNG with
    """
    import base64
    from Classifier.src.config import COLORS

    if "Residential" not in class_names:
        print("[DEBUG] Residential not found in cnames")
        return None

    residential_idx = class_names.index("Residential")
    residential_color = np.array(COLORS["Residential"])

    print(f"[DEBUG] MATCH: {residential_color}")

    residential_mask = np.all(classification_mask == residential_color, axis=-1)

    residential_pixel_count = np.sum(residential_mask)
    print(f"[DEBUG] pixel count {residential_pixel_count}")

    if residential_pixel_count == 0:
        print("[DEBUG] No pixels")
        return None

    h, w = residential_mask.shape
    output = np.zeros((h, w, 4), dtype=np.uint8)  # RGBA

    output[residential_mask, :3] = original[residential_mask]
    output[residential_mask, 3] = 255  # rgba+alpha

    print(f"[DEBUG] output: {output.shape}")
    _, buffer = cv2.imencode('.png', output)
    img_b64 = base64.b64encode(buffer).decode('utf-8')

    print("[DEBUG] to base64 PNG")

    return f"data:image/png;base64,{img_b64}"