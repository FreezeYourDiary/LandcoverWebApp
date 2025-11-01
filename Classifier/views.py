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
from django.shortcuts import render
from django.http import HttpResponse, Http404
def map_page(request):
    return render(request, 'map_analyze.html')

@csrf_exempt
def analyze_bbox(request):
    """  building blog main func.
    POST analysis, dzielony na funkcje produkcyjne extract, crop, run_analisys, smooth. etc"""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        bbox = payload.get("bbox")
        print("[DEBUG] Received bbox:", bbox)
        params = payload.get("params", {})
        model_path = payload.get("model_path")

        if not bbox or not model_path:
            return JsonResponse({"error": "Missing bbox or model_path"}, status=400)

        cache_key = make_cache_key(bbox, model_path, params)
        # existing = Analysis.objects.filter(cache_key=cache_key).first()
        # if existing:
        #     return JsonResponse({
        #         "cached": True,
        #         "analysis_id": existing.id,
        #         "stats": existing.stats,
        #         "paths": {
        #             "figure": existing.fig_path,
        #             "stats_json": existing.stats_json,
        #             "metadata": existing.metadata_json
        #         }
        #     })

        # TODO update modulate references
        mbtiles_path = os.path.join(settings.BASE_DIR, "data/raw/satellite-2017-11-02_europe_poland.mbtiles")
        if not os.path.exists(mbtiles_path):
            return JsonResponse({"error": f"Missing MBTiles at {mbtiles_path}"}, status=500)

        zoom = payload.get("zoom") or params.get("ZOOM", 8)
        print("[DEBUG] Received zoom:", zoom)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stitched_path = os.path.join(settings.MEDIA_ROOT, f"Classifier/outputs/stitched/area_{timestamp}.jpg")

        stitched_path = extract_tiles_from_mbtiles(
            mbtiles_path=mbtiles_path,
            bbox=bbox,
            zoom=zoom,
            output_path=stitched_path
        )

        cropped_path = crop_to_bbox(stitched_path, bbox, zoom)
        stitched_path = cropped_path
        if not os.path.exists(stitched_path):
            return JsonResponse({"error": "Failed to stitch area from MBTiles"}, status=500)

        # ─── run analysis ───────────────────────────────────────
        stats, outputs = run_analysis(image_path=stitched_path, model_path=model_path, options=params)

        # ─── save to DB ─────────────────────────────────────────
        a = Analysis.objects.create(
            image_path=stitched_path,
            model_path=model_path,
            config=params,
            stats=stats,
            metadata_json=outputs.get("metadata_json"),
            stats_json=outputs.get("stats_json"),
            fig_path=outputs.get("fig"),
            mask_path=outputs.get("mask_path") or outputs.get("mask"),
            change_log_path=outputs.get("change_log"),
            bbox_minx=bbox[0],
            bbox_miny=bbox[1],
            bbox_maxx=bbox[2],
            bbox_maxy=bbox[3],
            cache_key=cache_key
        )

        # ─── PREVIEW IMAGE TODO FETCH IMAGE I SHOW FULL TIME (ORYGINAL), LIKE CHATBOT UPDATE OTHER PARAMS
        preview_path = outputs.get("fig") or outputs.get("mask_path")
        img_b64 = None
        if preview_path and os.path.exists(preview_path):
            with open(preview_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

        return JsonResponse({
            "cached": False,
            "analysis_id": a.id,
            "stats": to_serializable(stats),
            "paths": to_serializable(outputs),
            "preview_image": f"data:image/png;base64,{img_b64}" if img_b64 else None
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
