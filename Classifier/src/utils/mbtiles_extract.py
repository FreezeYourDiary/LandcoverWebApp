import sqlite3
import mercantile
from PIL import Image
from io import BytesIO
import os
import math

def bbox_to_tiles(bbox, zoom):
    """return: all tile coordinates for a bounding -rectangle with data box."""
    west, south, east, north = bbox
    return list(mercantile.tiles(west, south, east, north, zoom))



def lonlat_to_pixel(lon, lat, zoom, tile_size=256):
    """convert lon/lat --- pixel coordinates with zoom in Web Mercator projection."""
    ''' 1. clamp lon/lat on poles ---> kwadratowa mapa
    2. normalizacja -180+180 na 0-1
    3. kalkulacja world width na poziomie zoom(zmienna) piksel = 2^zoom x tile_size 256 w mbtiles. '''
    lat = max(min(lat, 85.05112878), -85.05112878)
    x = (lon + 180.0) / 360.0 * (2.0 ** zoom * tile_size)
    y = ((1.0 - math.log(math.tan(math.radians(lat)) + 1.0 / math.cos(math.radians(lat))) / math.pi)
        / 2.0 * (2.0 ** zoom * tile_size))
    return x, y

def crop_to_bbox(stitched_path, bbox, zoom, tile_size=256):
    """Crop stitched to exact bbox [dla wlasciwej strony]"""
    ''' 1. switch y input |~ na |_
    2. ~
    3. crop znajdując różnicę między narożnikami 
    docelowego иBox a początkiem zszytego obrazu.'''
    west, south, east, north = bbox

    img = Image.open(stitched_path)
    x0_global, y1_global = lonlat_to_pixel(west, south, zoom, tile_size)
    x1_global, y0_global = lonlat_to_pixel(east, north, zoom, tile_size)

    # ~top left pixel of first tile
    tiles = list(mercantile.tiles(west, south, east, north, zoom))
    x_tiles = sorted({t.x for t in tiles})
    y_tiles = sorted({t.y for t in tiles})

    min_tile_x = min(x_tiles) * tile_size
    min_tile_y = min(y_tiles) * tile_size
    max_tile_x = (max(x_tiles) + 1) * tile_size
    max_tile_y = (max(y_tiles) + 1) * tile_size

    left = int(x0_global - min_tile_x)
    right = int(x1_global - min_tile_x)
    top = int(y0_global - min_tile_y)
    bottom = int(y1_global - min_tile_y)

    cropped = img.crop((left, top, right, bottom))

    cropped_path = os.path.splitext(stitched_path)[0] + "_cropped.jpg"
    cropped.save(cropped_path, "JPEG", quality=90)
    print(f"[DEBUG] cropped saved: {cropped_path} ({cropped.width}x{cropped.height})")

    return cropped_path


def extract_tiles_from_mbtiles(mbtiles_path, bbox, zoom, output_path, debug_dir=None):
    """Extract and stitch tiles that cover bbox. Optionally dump individual tiles."""
    conn = sqlite3.connect(mbtiles_path)
    cursor = conn.cursor()
    # tiles == lista indeksow {[x1,y1], ... [xn,yn]}
    tiles = bbox_to_tiles(bbox, zoom)

    # if not tiles:
    #     raise ValueError("No tiles found for bbox")
    if not tiles:
        raise ValueError(f"[DEBUG]: No tiles for bbox, {tiles}")
    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)

    # Read one tile to get size
    cursor.execute("SELECT tile_data FROM tiles WHERE zoom_level=? LIMIT 1", (zoom,))
    first_tile = cursor.fetchone()
    if not first_tile:
        raise ValueError(f"[DEBUG] No tiles for zoom {zoom}")
    tile_size = Image.open(BytesIO(first_tile[0])).width

    x_tiles = sorted({t.x for t in tiles})
    y_tiles = sorted({t.y for t in tiles})
    width = len(x_tiles) * tile_size
    height = len(y_tiles) * tile_size
    stitched = Image.new("RGB", (width, height))
    # {256x256}  zoom, column, row
    # bydgoszcz z=10, x=563, y=332
    print(f"[DEBUG] Tiles to stitch ({len(tiles)}):")
    for t in tiles:
        print(f"  -> z={t.z}, x={t.x}, y={t.y}")
        #  fix flipa y
        cursor.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
            (t.z, t.x, (1 << t.z) - 1 - t.y)
        )
        row = cursor.fetchone()
        if not row:
            print(f"[DEBUG] {t.z}/{t.x}/{t.y}") # w wyszukiwarce
            continue

        tile_img = Image.open(BytesIO(row[0])).convert("RGB")

        if debug_dir:
            tile_path = os.path.join(debug_dir, f"tile_{t.z}_{t.x}_{t.y}.jpg")
            tile_img.save(tile_path)
            print(f"     saved: {tile_path}")

        x_idx = x_tiles.index(t.x)
        y_idx = y_tiles.index(t.y)
        stitched.paste(tile_img, (x_idx * tile_size, y_idx * tile_size))

    print(f"[DEBUG] Stitched image shape: {stitched.width}x{stitched.height}")
    print(f"[DEBUG] Xs: {min(x_tiles)}–{max(x_tiles)} / Ys: {min(y_tiles)}–{max(y_tiles)}")

    conn.close()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    stitched.save(output_path, "JPEG", quality=90)

    return output_path
