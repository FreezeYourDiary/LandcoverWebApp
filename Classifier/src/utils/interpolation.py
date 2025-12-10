import cv2
import numpy as np


def apply_interpolation(prob_grid, target_width, target_height):
    return cv2.resize(prob_grid, (target_width, target_height), interpolation=cv2.INTER_LINEAR)


def simplify_predictions(predictions, class_names, class_mapping):
    """
    Convert original class predictions to simplified class predictions.
    """
    simplified_classes = sorted(set(v for v in class_mapping.values() if v is not None))

    print(f"[DEBUG SIMPLIFY] Original classes: {class_names}")
    print(f"[DEBUG SIMPLIFY] Simplified classes: {simplified_classes}")
    print(f"[DEBUG SIMPLIFY] Mapping: {class_mapping}")

    shape = predictions.shape[:-1]
    simplified_probs = np.zeros(shape + (len(simplified_classes),), dtype=float)

    for i, orig_class in enumerate(class_names):
        simplified_class = class_mapping.get(orig_class)
        if simplified_class is not None:
            j = simplified_classes.index(simplified_class)
            simplified_probs[..., j] += predictions[..., i]
            print(f"[DEBUG SIMPLIFY] {orig_class} (idx {i}) -> {simplified_class} (idx {j})")
        else:
            print(f"[DEBUG SIMPLIFY] {orig_class} (idx {i}) -> EXCLUDED (prob redistributed)")

    total = np.sum(simplified_probs, axis=-1, keepdims=True)
    total[total == 0] = 1e-9
    simplified_probs = simplified_probs / total

    print(f"[DEBUG SIMPLIFY] Output shape: {simplified_probs.shape}")

    return simplified_probs, simplified_classes