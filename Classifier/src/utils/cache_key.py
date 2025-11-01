# analyzer/utils.py
import hashlib
import json

def make_cache_key(bbox, model_path, params):
    """
    for db dostep
    bbox: tuple (minx, miny, maxx, maxy) floats, params: dict of analysis params (tile_size, img_size, smoothing, conf_thresh...)
    returns: hex klucz
    """
    key_obj = {
        "bbox": [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
        "model": model_path,
        "params": params
    }
    raw = json.dumps(key_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    h = hashlib.sha256(raw.encode("utf8")).hexdigest()
    return h[:32]
