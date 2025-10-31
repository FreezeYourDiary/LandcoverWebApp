import os
import sqlite3
from PIL import Image
from io import BytesIO

def mbtiles_to_jpg_tiles(mbtiles_path, output_dir):
    """
    each tile in MBTiles in  natural size
    """
    os.makedirs(output_dir, exist_ok=True)

    conn = sqlite3.connect(mbtiles_path)
    cursor = conn.cursor()
    cursor.execute("SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles")

    metadata = []

    for zoom, col, row, tile_data in cursor.fetchall():
        tile = Image.open(BytesIO(tile_data))
        tile = tile.convert("RGB")

        tile_name = f"z{zoom}_x{col}_y{row}.jpg"
        tile_path = os.path.join(output_dir, tile_name)
        tile.save(tile_path, "JPEG", quality=90)

        metadata.append({
            "file": tile_name,
            "zoom": zoom,
            "tile_col": col,
            "tile_row": row,
        })

    conn.close()
    return metadata

if __name__ == '__main__':
    mbtiles_file = "data/raw/satellite-2017-11-02_europe_poland.mbtiles"
    output_folder = "data/processed/img-polska"

    metadata = mbtiles_to_jpg_tiles(mbtiles_file, output_folder)
