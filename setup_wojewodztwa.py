"""
script-test sprawzajacy integrity plikow
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LandcoverWebApp.settings')
django.setup()
from django.conf import settings
from Classifier.src.utils.wojewodztwo_processor import load_wojewodztwa_geojson


def check_files():
    print("=" * 60)
    print("CHECKING REQUIRED FILES")
    print("=" * 60)

    checks = {
        "GeoJSON file": os.path.join(
            settings.BASE_DIR,
            "Classifier/static/geodata/wojewodztwa-max.geojson"
        ),
        "MBTiles file": os.path.join(
            settings.BASE_DIR,
            "data/raw/satellite-2017-11-02_europe_poland.mbtiles"
        ),
        "Output directory": os.path.join(
            settings.MEDIA_ROOT,
            "Classifier/outputs/wojewodztwa"
        ),
    }

    all_ok = True
    for name, path in checks.items():
        exists = os.path.exists(path)
        status = "+" if exists else "-"
        print(f"{status} {name}: {path}")
        if not exists:
            all_ok = False
            if "directory" in name.lower():
                print(f"  → Creating directory...")
                os.makedirs(path, exist_ok=True)

    print()
    return all_ok


def check_geojson():
    print("=" * 60)
    print("CHECKING GEOJSON DATA")
    print("=" * 60)

    try:
        geojson_path = os.path.join(
            settings.BASE_DIR,
            "Classifier/static/geodata/wojewodztwa-max.geojson"
        )

        wojewodztwa = load_wojewodztwa_geojson(geojson_path)

        print(f"loaded {len(wojewodztwa)} województwa")
        print("\nWojewództwa list:")
        for w in wojewodztwa:
            print(f"  - ID {w['id']:2d}: {w['nazwa']:20s} | Bounds: {w['bounds']}")

        print()
        return True
    except Exception as e:
        print(f"Error loading GeoJSON: {e}")
        print()
        return False


def check_models():
    print("=" * 60)
    print("CHECKING DATABASE")
    print("=" * 60)

    try:
        from Classifier.models import WojewodztwoAnalysis

        count = WojewodztwoAnalysis.objects.count()
        print(f"Database accessible")
        print(f"Existing analyses: {count}")

        if count > 0:
            latest = WojewodztwoAnalysis.objects.order_by('-created_at').first()
            print(f"  Latest: {latest.wojewodztwo_name} ({latest.created_at})")

        print()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        print("migrations issue")
        return False

def test_geometry_processing():
    """Test geometry processing functions."""
    print("=" * 60)
    print("TESTING GEOMETRY PROCESSING")
    print("=" * 60)

    try:
        import numpy as np
        from shapely.geometry import Polygon
        from Classifier.src.utils.wojewodztwo_processor import create_mask_from_geometry

        # polygon load test
        test_geom = Polygon([
            (0, 0), (1, 0), (1, 1), (0, 1), (0, 0)
        ])
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mask = create_mask_from_geometry(
            test_image.shape,
            test_geom,
            bounds=[0, 0, 1, 1],
            zoom=8
        )

        if mask.shape == (100, 100):
            print(f"+ Mask creation works")
            print(f"  Mask shape: {mask.shape}")
            print(f"  Non-zero pixels: {np.count_nonzero(mask)}")
        else:
            print(f"- MAsk shape: {mask.shape}")
            return False

        print()
        return True
    except Exception as e:
        print(f"- Geometry processing error: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """Run all checks."""
    print("\n" + "=" * 60)
    print("WOJEWÓDZTWA ANALYSIS SYSTEM - SETUP CHECK")
    print("=" * 60 + "\n")

    results = {
        "Files": check_files(),
        "GeoJSON": check_geojson(),
        "Database": check_models(),
        "Geometry Processing": test_geometry_processing(),
    }

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for check, passed in results.items():
        status = "+ PASS" if passed else "- FAIL"
        print(f"{status}: {check}")

    all_passed = all(results.values())

    print()
    if all_passed:
        print("+ ALL CHECKS PASSED!")
    else:
        print("- CHECKS FAILED")

    print("=" * 60 + "\n")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())