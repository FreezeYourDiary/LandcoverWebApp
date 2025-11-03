# analyzer/views.py
import os
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from datetime import datetime
from django.conf import settings
import base64
from Classifier.src.utils.convert import to_serializable
from Classifier.src.utils.mbtiles_extract import extract_tiles_from_mbtiles, crop_to_bbox
from Classifier.models import Analysis
from src.utils.cache_key import make_cache_key
from src.pipeline import run_analysis
import sqlite3
import numpy as np
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404
from Classifier.src.stats import *
def map_page(request):
    return render(request, 'map_analyze.html')

@csrf_exempt
def analyze_bbox(request):
    """
    Main analysis endpoint.
    Supports:
    - POST only
    - MBTiles extraction
    - Crop/full MBTiles mode
    - Storing results in Analysis model
    - Returning JSON stats + preview image
    - Returns incremental 'progress' updates to frontend
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        bbox = payload.get("bbox")
        params = payload.get("params", {})
        model_path = payload.get("model_path")
        mode = payload.get("mode", "cropped")  # "cropped" or "full"
        zoom = payload.get("zoom") or params.get("ZOOM", 8)

        if not bbox or not model_path:
            return JsonResponse({"error": "Missing bbox or model_path"}, status=400)

        cache_key = make_cache_key(bbox, model_path, params)
        mbtiles_path = os.path.join(settings.BASE_DIR, "data/raw/satellite-2017-11-02_europe_poland.mbtiles")
        if not os.path.exists(mbtiles_path):
            return JsonResponse({"error": f"Missing MBTiles at {mbtiles_path}"}, status=500)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stitched_path = os.path.join(settings.MEDIA_ROOT, f"Classifier/outputs/stitched/area_{timestamp}.jpg")

        stitched_path = extract_tiles_from_mbtiles(
            mbtiles_path=mbtiles_path,
            bbox=bbox,
            zoom=zoom,
            output_path=stitched_path
        )

        if not os.path.exists(stitched_path):
            return JsonResponse({"error": "Failed to stitch area from MBTiles"}, status=500)

        if mode == "cropped":
            cropped_path = crop_to_bbox(stitched_path, bbox, zoom)
        else:
            cropped_path = stitched_path  # full image mode

        full_img = cv2.imread(stitched_path)
        overlay = full_img.copy()
        h, w, _ = full_img.shape

        color = (0, 255, 0)  
        thickness = 3
        cv2.rectangle(overlay, (10, 10), (w - 10, h - 10), color, thickness)
        alpha = 0.4
        preview_img = cv2.addWeighted(overlay, alpha, full_img, 1 - alpha, 0)

        preview_overlay_path = os.path.join(
            settings.MEDIA_ROOT, f"Classifier/outputs/stitched/area_{timestamp}_overlay.jpg"
        )
        cv2.imwrite(preview_overlay_path, preview_img)

        stats, outputs = run_analysis(image_path=cropped_path, model_path=model_path, options=params)

        mask_path = outputs.get("mask_path") or outputs.get("mask")
        if isinstance(mask_path, list):
            mask_path = mask_path[0] if mask_path else None

        if not mask_path or not isinstance(mask_path, (str, bytes, os.PathLike)) or not os.path.exists(mask_path):
            print("[WARN] No valid mask_path:", mask_path)
            mask_path = None

        stats_clean = normalize_stats(stats)

        a = Analysis.objects.create(
            image_path=cropped_path,
            model_path=model_path,
            config=params,
            stats=stats_clean,
            metadata_json=outputs.get("metadata_json"),
            stats_json=outputs.get("stats_json"),
            fig_path=outputs.get("fig"),
            mask_path=mask_path,
            change_log_path=outputs.get("change_log"),
            bbox_minx=bbox[0],
            bbox_miny=bbox[1],
            bbox_maxx=bbox[2],
            bbox_maxy=bbox[3],
            cache_key=cache_key
        )

        preview_path = outputs.get("fig") or mask_path or preview_overlay_path
        img_b64 = None
        if preview_path and os.path.exists(preview_path):
            with open(preview_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")


        return JsonResponse({
            "cached": False,
            "analysis_id": a.id,
            "stats": stats_clean,
            "tabs": [
                {"key": "area", "label": "Area (km²)", "data": stats_clean["areas_sq_km"]},
                {"key": "percentage", "label": "Area (%)", "data": stats_clean["areas_pct"]},
                {"key": "density", "label": "Density", "data": stats_clean["density"]},
                {"key": "fragmentation", "label": "Fragmentation", "data": stats_clean["fragmentation"]},
                {"key": "adjacency", "label": "Adjacency Matrix", "data": stats_clean["adjacency"]},
            ],
            "paths": to_serializable(outputs),
            "preview_image": f"data:image/jpeg;base64,{img_b64}" if img_b64 else None,
            "progress": [
                {"step": "extracting_tiles", "label": "Extracting map tiles", "done": True},
                {"step": "cropping", "label": "Cropping area", "done": mode == "cropped"},
                {"step": "analyzing", "label": "Analyzing area", "done": True},
                {"step": "saving", "label": "Saving results", "done": True},
            ]
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

def tile_from_mbtiles(request, z, x, y):
    mbtiles_path = "data/raw/satellite-2017-11-02_europe_poland.mbtiles"
    conn = sqlite3.connect(mbtiles_path)
    cur = conn.cursor()
    cur.execute("SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?", (z, x, y))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise Http404("Tile not found")
    return HttpResponse(row[0], content_type="image/jpeg")

from django.http import FileResponse

def get_analysis_stats(request, analysis_id):
    """Return stats for a given Analysis record."""
    try:
        a = Analysis.objects.get(pk=analysis_id)
        if "download" in request.GET:
            json_path = a.stats_json or None
            if json_path and os.path.exists(json_path):
                return FileResponse(open(json_path, "rb"), as_attachment=True, filename=f"analysis_{a.id}_stats.json")
            else:
                return JsonResponse({"error": "No stats JSON stored."}, status=404)
        return JsonResponse(a.serialize())
    except Analysis.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

#  use in stats generation for stat data for city
# @csrf_exempt
# def analyze_area(request):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         stats, outputs = run_analysis("data/real/raw2.jpg")
#         return JsonResponse({"status": "done", "outputs": outputs})
#     return JsonResponse({"error": "Invalid method"}, status=405)

def map_view(request):
    return render(request, "map.html")
def base_view(request):
    return render(request, 'base.html', {'title': 'base'})

def city(request, city_name):
    # Dummy dataset
    dummy = [
        {
            'name': 'wroclaw',
            'display_name': 'Wrocław',
            'area': 292.9,
            'population': 640000,
            'green_space_percent': 27.5,
            'maps': [
                {'title': 'Landcover Classification', 'path': '/tiles/wroclaw_landcover/{z}/{x}/{y}.jpg'},
                {'title': 'Vegetation Index (NDVI)', 'path': '/tiles/wroclaw_ndvi/{z}/{x}/{y}.jpg'},
                {'title': 'Water Bodies Mask', 'path': '/tiles/wroclaw_water/{z}/{x}/{y}.jpg'}
            ]
        },
        {
            'name': 'krakow',
            'display_name': 'Kraków',
            'area': 326.8,
            'population': 780000,
            'green_space_percent': 22.3,
            'maps': [
                {'title': 'Landcover Classification', 'path': '/tiles/krakow_landcover/{z}/{x}/{y}.jpg'},
                {'title': 'Urban Heat Map', 'path': '/tiles/krakow_heat/{z}/{x}/{y}.jpg'}
            ]
        },
    ]

    city_obj = next((c for c in dummy if c['name'] == city_name.lower()), None)
    if not city_obj:
        raise Http404("City not found")

    stats = {
        'Area (km²)': city_obj['area'],
        'Population': city_obj['population'],
        'Green Spaces (%)': city_obj['green_space_percent'],
    }

    context = {
        'title': f"Statistics for {city_obj['display_name']}",
        'city': city_obj,
        'stats': stats,
        'maps': city_obj.get('maps', []),
    }
    return render(request, 'jednostka.html', context)