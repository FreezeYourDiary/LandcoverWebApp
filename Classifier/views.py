# analyzer/views.py
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from datetime import datetime
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404
import base64
import sqlite3

from Classifier.src.utils.convert import to_serializable
from Classifier.src.utils.mbtiles_extract import extract_tiles_from_mbtiles, crop_to_bbox
from Classifier.models import Analysis, WojewodztwoAnalysis
from Classifier.src.stats import *
from Classifier.src.utils.wojewodztwo_processor import *
from src.utils.cache_key import make_cache_key
from src.pipeline import run_analysis

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

def city_tile_from_mbtiles(request, city, z, x, y):
    """
    Serve tiles from a city-specific MBTiles file.
    Example path: data/raw/satellite-2017-11-02_poland_wroclaw.mbtiles
    """
    mbtiles_path = os.path.join(settings.BASE_DIR, f"data/raw/satellite-2017-11-02_poland_{city.lower()}.mbtiles")

    if not os.path.exists(mbtiles_path):
        # optional: fallback to main file
        fallback_path = os.path.join(settings.BASE_DIR, "data/raw/satellite-2017-11-02_europe_poland.mbtiles")
        if os.path.exists(fallback_path):
            mbtiles_path = fallback_path
        else:
            raise Http404(f"No MBTiles found for {city}")

    conn = sqlite3.connect(mbtiles_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
        (z, x, (1 << z) - 1 - y)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise Http404(f"Tile {z}/{x}/{y} not found for {city}")

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


def wojewodztwa_list_view(request):
    """
    Template: wojewodztwa_list.html
    """
    geojson_path = os.path.join(
        settings.BASE_DIR,
        "Classifier/static/geodata/wojewodztwa-max.geojson"
    )
    wojewodztwa = load_wojewodztwa_geojson(geojson_path)
    # mark analyzed
    analyzed = WojewodztwoAnalysis.objects.values_list('wojewodztwo_id', flat=True)
    analyzed_set = set(analyzed)
    for w in wojewodztwa:
        w['analyzed'] = w['id'] in analyzed_set
        analysis = WojewodztwoAnalysis.objects.filter(
            wojewodztwo_id=w['id']
        ).order_by('-created_at').first()
        w['last_analysis'] = analysis.created_at if analysis else None

    return render(request, 'wojewodztwa_list.html', {
        'wojewodztwa': wojewodztwa,
        'title': 'Województwa Analysis'
    })


def wojewodztwo_detail_view(request, wojewodztwo_id):
    """
    Template: wojewodztwo_detail.html
    """
    geojson_path = os.path.join(
        settings.BASE_DIR,
        "Classifier/static/geodata/wojewodztwa-max.geojson"
    )

    wojewodztwa = load_wojewodztwa_geojson(geojson_path)
    wojewodztwo = next((w for w in wojewodztwa if w['id'] == wojewodztwo_id), None)

    if not wojewodztwo:
        raise Http404("Województwo not found")

    analysis = WojewodztwoAnalysis.objects.filter(
        wojewodztwo_id=wojewodztwo_id
    ).order_by('-created_at').first()

    poland_averages = None
    if analysis:
        all_analyses = WojewodztwoAnalysis.objects.all()
        if all_analyses.exists():
            poland_averages = calculate_poland_averages(all_analyses)

    bounds = wojewodztwo['bounds']
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    context = {
        'wojewodztwo': {
            'id': wojewodztwo['id'],
            'name': wojewodztwo['nazwa'],
            'display_name': wojewodztwo['nazwa'].capitalize(),
            'latitude': center_lat,
            'longitude': center_lon,
            'bounds': bounds,
            'geometry': json.dumps(wojewodztwo['geometry'])
        },
        'title': f"Analysis for {wojewodztwo['nazwa'].capitalize()}",
        'has_analysis': analysis is not None,
        'poland_averages': json.dumps(poland_averages) if poland_averages else None,
    }

    if analysis:
        stats = analysis.stats
        tabs = [
            {"key": "area", "label": "Area (km²)", "data": stats.get("areas_sq_km", {})},
            {"key": "percentage", "label": "Area (%)", "data": stats.get("areas_pct", {})},
            {"key": "density", "label": "Density", "data": stats.get("density")},
            {"key": "adjacency", "label": "Adjacency Matrix", "data": stats.get("adjacency", {})},
        ]
        #  todo dla ogolnych stats dodac indeksy ndvi ndwi
        wojewodztwo_stats = {
            'Total Area': f"{analysis.total_area_km2:.2f} km²" if analysis.total_area_km2 else "N/A",
            'Analysis Date': analysis.created_at.strftime("%Y-%m-%d %H:%M"),
            'Model': os.path.basename(analysis.model_path),
        }

        original_image = None
        mask_image = None
        blended_image = None

        if analysis.cropped_image_path and os.path.exists(analysis.cropped_image_path):
            with open(analysis.cropped_image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                original_image = f"data:image/jpeg;base64,{img_b64}"

        if analysis.mask_path and os.path.exists(analysis.mask_path):
            with open(analysis.mask_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                mask_image = f"data:image/png;base64,{img_b64}"

        if analysis.fig_path and os.path.exists(analysis.fig_path):
            with open(analysis.fig_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                blended_image = f"data:image/png;base64,{img_b64}"

        context.update({
            'analysis': analysis,
            'stats_json': json.dumps(stats),
            'tabs_json': json.dumps(tabs),
            'wojewodztwo_stats': wojewodztwo_stats,
            'original_image': original_image,
            'mask_image': mask_image,
            'blended_image': blended_image,
        })

    return render(request, 'wojewodztwo_detail.html', context)


def calculate_poland_averages(analyses):
    total_stats = {
        "areas_pct": {},
        "fragmentation": {}
    }
    density_sum = 0
    density_count = 0

    count = 0
    for analysis in analyses:
        stats = analysis.stats
        if not stats:
            continue

        count += 1
        for class_name, value in stats.get("areas_pct", {}).items():
            if class_name not in total_stats["areas_pct"]:
                total_stats["areas_pct"][class_name] = 0
            total_stats["areas_pct"][class_name] += value

        for class_name, value in stats.get("fragmentation", {}).items():
            if class_name not in total_stats["fragmentation"]:
                total_stats["fragmentation"][class_name] = 0
            total_stats["fragmentation"][class_name] += value

        density_value = stats.get("density")
        if density_value is not None and isinstance(density_value, (int, float)):
            density_sum += density_value
            density_count += 1

    if count == 0:
        return None
    averages = {
        "areas_pct": {k: v / count for k, v in total_stats["areas_pct"].items()},
        "fragmentation": {k: v / count for k, v in total_stats["fragmentation"].items()},
        "density": density_sum / density_count if density_count > 0 else 0
    }

    return averages


@csrf_exempt
def analyze_wojewodztwo(request):
    """
    API endpoint - tworzy analize wojewodztwa
    POST /api/analyze-wojewodztwo/
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        payload = json.loads(request.body.decode("utf-8"))
        wojewodztwo_id = payload.get("wojewodztwo_id")
        model_path = payload.get("model_path")
        params = payload.get("params", {})
        zoom = payload.get("zoom", 8)
        force_recompute = payload.get("force_recompute", False)

        if not wojewodztwo_id or not model_path:
            return JsonResponse({"error": "Missing wojewodztwo_id or model_path"}, status=400)

        geojson_path = os.path.join(
            settings.BASE_DIR,
            "Classifier/static/geodata/wojewodztwa-max.geojson"
        )
        wojewodztwa = load_wojewodztwa_geojson(geojson_path)
        wojewodztwo = next((w for w in wojewodztwa if w['id'] == wojewodztwo_id), None)
        if not wojewodztwo:
            return JsonResponse({"error": f"Województwo {wojewodztwo_id} not found"}, status=404)

        cache_key = make_wojewodztwo_cache_key(wojewodztwo_id, model_path, params)

        if not force_recompute:
            cached = WojewodztwoAnalysis.objects.filter(cache_key=cache_key).first()
            if cached:
                return JsonResponse({
                    "cached": True,
                    "analysis_id": cached.id,
                    "message": "Using cached analysis",
                    "redirect_url": f"/wojewodztwo/{wojewodztwo_id}/"
                })
        mbtiles_path = os.path.join(
            settings.BASE_DIR,
            "data/raw/satellite-2017-11-02_europe_poland.mbtiles"
        )
        if not os.path.exists(mbtiles_path):
            return JsonResponse({"error": f"MBTiles not found: {mbtiles_path}"}, status=500)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wojewodztwo_slug = unify_lang_file(wojewodztwo['nazwa'])

        output_base = os.path.join(
            settings.MEDIA_ROOT,
            f"Classifier/outputs/wojewodztwa/{wojewodztwo_slug}"
        )
        os.makedirs(output_base, exist_ok=True)
        conn = sqlite3.connect(mbtiles_path)
        cur = conn.cursor()
        cur.execute("SELECT MAX(zoom_level) FROM tiles")
        max_zoom_result = cur.fetchone()
        conn.close()

        max_available_zoom = max_zoom_result[0] if max_zoom_result and max_zoom_result[0] else 13
        # max or specified
        actual_zoom = min(zoom, max_available_zoom)

        print(f"[INFO]zoom level {actual_zoom} (max available: {max_available_zoom})")
        stitched_path = os.path.join(
            output_base,
            f"{wojewodztwo_slug}_{timestamp}_stitched.jpg"
        )

        bbox = wojewodztwo['bounds']
        stitched_path = extract_tiles_from_mbtiles(
            mbtiles_path=mbtiles_path,
            bbox=bbox,
            zoom=actual_zoom,
            output_path=stitched_path
        )

        if not os.path.exists(stitched_path):
            return JsonResponse({"error": "Failed to extract tiles"}, status=500)

        # maska
        img = cv2.imread(stitched_path)
        if img is None:
            return JsonResponse({
                "error": f"Failed to read extracted image: {stitched_path}"
            }, status=500)
        # specyficzne for wojewodztwo_processor
        mask = create_mask_from_geometry(
            img.shape,
            wojewodztwo['shapely_geom'],
            bbox,
            actual_zoom
        )
        cropped_path = os.path.join(
            output_base,
            f"{wojewodztwo_slug}_{timestamp}_cropped.jpg"
        )
        cropped_path, cropped_mask, crop_offset = crop_image_by_mask(
            stitched_path, mask, cropped_path
        )

        stats, outputs = run_analysis(
            image_path=cropped_path,
            model_path=model_path,
            options={
                **params,
                'mask': cropped_mask,
                'zoom': actual_zoom,
                'bounds': bbox
            }
        )

        mask_path = outputs.get("mask_path") or outputs.get("mask")
        blended_path = outputs.get("blended_path") or outputs.get("blended")

        if isinstance(mask_path, list):
            mask_path = mask_path[0] if mask_path else None
        stats_clean = normalize_stats(stats)
        total_area_km2 = calculate_geospat(wojewodztwo['shapely_geom'])
        analysis = WojewodztwoAnalysis.objects.create(
            wojewodztwo_id=wojewodztwo['id'],
            wojewodztwo_name=wojewodztwo['nazwa'],
            geometry=wojewodztwo['geometry'],
            bounds=bbox,
            model_path=model_path,
            config=params,
            zoom=actual_zoom,
            original_image_path=stitched_path,
            cropped_image_path=cropped_path,
            mask_path=mask_path if mask_path and os.path.exists(str(mask_path)) else None,
            fig_path=blended_path if blended_path and os.path.exists(str(blended_path)) else None,
            stats=stats_clean,
            stats_json=outputs.get("stats_json"),
            metadata_json=outputs.get("metadata_json"),
            change_log_path=outputs.get("change_log"),
            total_area_km2=total_area_km2,
            cache_key=cache_key
        )

        return JsonResponse({
            "success": True,
            "cached": False,
            "analysis_id": analysis.id,
            "message": "Analysis completed successfully",
            "redirect_url": f"/wojewodztwo/{wojewodztwo_id}/"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


def wojewodztwo_tiles(request, wojewodztwo_id, z, x, y):
    """
    provide
    GET /wojewodztwo_tiles/<wojewodztwo_id>/{z}/{x}/{y}.jpg - same process for /tiles/
    """
    mbtiles_path = os.path.join(
        settings.BASE_DIR,
        "data/raw/satellite-2017-11-02_europe_poland.mbtiles"
    )

    if not os.path.exists(mbtiles_path):
        raise Http404("MBTiles file not found")

    try:
        conn = sqlite3.connect(mbtiles_path)
        cur = conn.cursor()

        # MBTiles uses TMS, so we need to flip Y
        # For TMS: y_tms = (2^z - 1) - y_xyz
        y_tms = (2 ** int(z) - 1) - int(y)

        cur.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
            (z, x, y_tms)
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            raise Http404("Tile not found")

        return HttpResponse(row[0], content_type="image/jpeg")

    except Exception as e:
        raise Http404(f"Error fetching tile: {e}")

def api_list_wojewodztwa(request):
    """
    fetch analysis status
    """
    geojson_path = os.path.join(
        settings.BASE_DIR,
        "Classifier/static/geodata/wojewodztwa-max.geojson"
    )

    wojewodztwa = load_wojewodztwa_geojson(geojson_path)
    analyzed_ids = set(
        WojewodztwoAnalysis.objects.values_list('wojewodztwo_id', flat=True)
    )
    result = []
    for w in wojewodztwa:
        result.append({
            'id': w['id'],
            'nazwa': w['nazwa'],
            'bounds': w['bounds'],
            'analyzed': w['id'] in analyzed_ids,
            'geometry': w['geometry']
        })

    return JsonResponse({'wojewodztwa': result})

def history(request):
    """
    history
    """
    from Classifier.models import Analysis, WojewodztwoAnalysis
    bbox_analyses = Analysis.objects.all().order_by('-created_at')
    woj_analyses = WojewodztwoAnalysis.objects.all().order_by('-created_at')

    analyses_data = []

    for analysis in bbox_analyses:
        files_available = {
            'stats_json': analysis.stats_json and os.path.exists(analysis.stats_json),
            'metadata_json': analysis.metadata_json and os.path.exists(analysis.metadata_json),
            'fig': analysis.fig_path and os.path.exists(analysis.fig_path),
            'mask': analysis.mask_path and os.path.exists(analysis.mask_path),
        }

        analyses_data.append({
            'type': 'bbox',
            'id': analysis.id,
            'timestamp': analysis.created_at,
            'stats': analysis.stats or {},
            'preview_path': analysis.fig_path or analysis.mask_path,  # Store path, not base64
            'model': os.path.basename(analysis.model_path) if analysis.model_path else 'Unknown',
            'files': files_available,
        })

    for analysis in woj_analyses:
        files_available = {
            'stats_json': analysis.stats_json and os.path.exists(analysis.stats_json),
            'metadata_json': analysis.metadata_json and os.path.exists(analysis.metadata_json),
            'fig': analysis.fig_path and os.path.exists(analysis.fig_path),
            'mask': analysis.mask_path and os.path.exists(analysis.mask_path),
        }

        analyses_data.append({
            'type': 'wojewodztwo',
            'id': analysis.id,
            'wojewodztwo_name': analysis.wojewodztwo_name,
            'timestamp': analysis.created_at,
            'stats': analysis.stats or {},
            'preview_path': analysis.fig_path or analysis.mask_path,  # Store path, not base64
            'model': os.path.basename(analysis.model_path) if analysis.model_path else 'Unknown',
            'total_area_km2': analysis.total_area_km2,
            'files': files_available,
        })

    analyses_data.sort(key=lambda x: x['timestamp'], reverse=True)
    # updated. znaczniki paginatory to lepszej load strony
    paginator = Paginator(analyses_data, 21)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'history.html', {
        'page_obj': page_obj,
        'total_count': len(analyses_data),
        'title': 'All Analyses'
    })


def get_analysis_preview(request, analysis_type, analysis_id):
    """
    preview for history
    """
    try:
        if analysis_type == 'bbox':
            analysis = Analysis.objects.get(id=analysis_id)
        else:
            analysis = WojewodztwoAnalysis.objects.get(id=analysis_id)

        preview_path = analysis.fig_path or analysis.mask_path

        if not preview_path or not os.path.exists(preview_path):
            return HttpResponse("Image not found", status=404)
        allowed_dirs = [
            os.path.join(settings.MEDIA_ROOT, 'Classifier/outputs'),
            os.path.join(settings.BASE_DIR, 'Classifier/outputs'),
        ]

        file_abs = os.path.abspath(preview_path)
        if not any(file_abs.startswith(os.path.abspath(d)) for d in allowed_dirs):
            return HttpResponse("Access denied", status=403)

        # Serve image
        return FileResponse(open(preview_path, 'rb'), content_type='image/png')

    except (Analysis.DoesNotExist, WojewodztwoAnalysis.DoesNotExist):
        return HttpResponse("Analysis not found", status=404)


def download_analysis_file(request, analysis_type, analysis_id, file_type):
    """
    analysis_type: bbox, wojewodztwo
    file_type: fig, metadata, mask
    """
    try:
        if analysis_type == 'bbox':
            analysis = Analysis.objects.get(id=analysis_id)
        elif analysis_type == 'wojewodztwo':
            analysis = WojewodztwoAnalysis.objects.get(id=analysis_id)
        else:
            return HttpResponse("Invalid analysis type", status=400)

        file_path_map = {
            'stats_json': analysis.stats_json,
            'metadata_json': analysis.metadata_json,
            'fig': analysis.fig_path,
            'mask': analysis.mask_path,
        }

        file_path = file_path_map.get(file_type)

        if not file_path or not os.path.exists(file_path):
            return HttpResponse("File not found", status=404)

    except (Analysis.DoesNotExist, WojewodztwoAnalysis.DoesNotExist):
        return HttpResponse("Analysis not found", status=404)
    allowed_dirs = [
        os.path.join(settings.MEDIA_ROOT, 'Classifier/outputs'),
        os.path.join(settings.BASE_DIR, 'Classifier/outputs'),
    ]
    # upd z mask
    file_abs = os.path.abspath(file_path)
    if not any(file_abs.startswith(os.path.abspath(d)) for d in allowed_dirs):
        return HttpResponse("Access denied", status=403)
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read())
        if file_path.endswith('.json'):
            response['Content-Type'] = 'application/json'
        elif file_path.endswith('.png'):
            response['Content-Type'] = 'image/png'
        elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
            response['Content-Type'] = 'image/jpeg'
        elif file_path.endswith('.zip'):
            response['Content-Type'] = 'application/zip'

        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response
