import json
import geopandas as gpd
from pprint import pprint

''' OUTPUTS - geojson file, features count'''
path = "Classifier/static/geodata/wojewodztwa-max.geojson"

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Features count: {len(data['features'])}")
print("properties:")
pprint(data["features"][0]["properties"])

gdf = gpd.read_file(path)
print("\nColumns:", gdf.columns.tolist())
print("\nrow:")
print(gdf.iloc[0])
''' revert to gebounds w cropping'''
print("\nGeobounds:", gdf.iloc[0].geometry.bounds)
