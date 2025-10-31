import numpy as np


def convert_to_float(obj):
    """numpy to python"""
    if isinstance(obj, dict):
        return {k: convert_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_float(elem) for elem in obj]
    elif isinstance(obj, np.generic):
        return obj.item()
    return obj