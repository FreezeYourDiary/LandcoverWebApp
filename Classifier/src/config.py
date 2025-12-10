DEFAULT_CONFIG = {
    "MODEL_PATH": "Classifier/inputs/networks/mobilenetv2_v3.keras",
    "IMG_SIZE": 64,
    "TILE_SIZE": 32,
    "CONF_THRESH": 0.6,
    "APPLY_SMOOTHING": True,
    "APPLY_INTERPOLATION": False,  # +
    "USE_SIMPLIFIED_CLASSES": False,  # +
    "NEIGHBORHOOD": 3,
    "OUTPUT_BASE_DIR": "outputs/results",
    "MAP_PATH": "data/raw/satellite-2017-11-02_europe_poland.mbtiles"
}

CLASS_NAMES = [
    "AnnualCrop", "Forest", "HerbaceousVegetation",
    "Highway", "Industrial", "Pasture",
    "PermanentCrop", "Residential", "River", "SeaLake"
]

SIMPLIFIED_CLASS_NAMES = [
    "AnnualCrop", "Forest", "HerbaceousVegetation",
    "Pasture", "PermanentCrop", "Residential", "River", "SeaLake"
]

CLASS_MAPPING = {
    "AnnualCrop": "AnnualCrop",
    "Forest": "Forest",
    "HerbaceousVegetation": "Forest",  #+forest
    "Highway": None,
    "Industrial": None,
    "Pasture": "Pasture",
    "PermanentCrop": "PermanentCrop",
    "Residential": "Residential",
    "River": "River",
    "SeaLake": "SeaLake"
}

COLORS = {
    "AnnualCrop": (255, 255, 0),
    "Forest": (0, 255, 0),
    "HerbaceousVegetation": (100, 200, 100),
    "Highway": (0, 0, 255),
    "Industrial": (128, 128, 128),
    "Pasture": (0, 200, 0),
    "PermanentCrop": (200, 255, 100),
    "Residential": (255, 255, 255),
    "River": (0, 255, 255),
    "SeaLake": (255, 100, 255),
}

CLASS_PRIORITY = {
    "River": 1.0,
    "Highway": 0.8,
    "Residential": 1.0,
    "Industrial": 1.1,
    "Pasture": 0.8,
    "Forest": 1.2
}