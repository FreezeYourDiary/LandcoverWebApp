# models.py
from django.db import models
from django.utils import timezone

class TileSource(models.Model):
    """each tile metadata"""
    name = models.CharField(max_length=100)
    path = models.CharField(max_length=1024)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Analysis(models.Model):
    """A single analysis run (cached)."""
    created_at = models.DateTimeField(default=timezone.now)

    image_path = models.CharField(max_length=1024)
    model_path = models.CharField(max_length=1024)
    config = models.JSONField()
    cache_key = models.CharField(max_length=128, unique=True)

    stats = models.JSONField(null=True, blank=True)
    class_percentages = models.JSONField(null=True, blank=True)
    fragmentation = models.JSONField(null=True, blank=True)
    density = models.FloatField(null=True, blank=True)
    adjacency = models.JSONField(null=True, blank=True)

    metadata_json = models.CharField(max_length=1024, blank=True, null=True)
    stats_json = models.CharField(max_length=1024, blank=True, null=True)
    fig_path = models.CharField(max_length=1024, blank=True, null=True)
    mask_path = models.CharField(max_length=1024, blank=True, null=True)
    change_log_path = models.CharField(max_length=1024, blank=True, null=True)

    bbox_minx = models.FloatField(null=True, blank=True)
    bbox_miny = models.FloatField(null=True, blank=True)
    bbox_maxx = models.FloatField(null=True, blank=True)
    bbox_maxy = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Analysis {self.id} at {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

    def serialize(self):
        """API THEN"""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "image_path": self.image_path,
            "model_path": self.model_path,
            "stats": self.stats,
            "class_percentages": self.class_percentages,
            "fragmentation": self.fragmentation,
            "density": self.density,
            "adjacency": self.adjacency,
            "fig_path": self.fig_path,
            "mask_path": self.mask_path,
        }

# obsolete
class City(models.Model):
    name = models.CharField(max_length=128, unique=True)          # lowercase wroclaw? no id?
    display_name = models.CharField(max_length=256)
    bbox_minx = models.FloatField()
    bbox_miny = models.FloatField()
    bbox_maxx = models.FloatField()
    bbox_maxy = models.FloatField()
    tiles_prefix = models.CharField(max_length=256, blank=True, null=True)
    population = models.IntegerField(null=True, blank=True)
    area_km2 = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name

    def bbox(self):
        return [self.bbox_minx, self.bbox_miny, self.bbox_maxx, self.bbox_maxy]


class WojewodztwoAnalysis(models.Model):
    """
    Based on GeoJSON boundaries, MBTiles, CNN classification.
    """
    # Identification
    wojewodztwo_id = models.IntegerField(help_text="ID from GeoJSON")
    wojewodztwo_name = models.CharField(max_length=100, help_text="Nazwa from GeoJSON")
    # geojson outputs
    # id 1
    # nazwa śląskie
    # geometry MULTIPOLYGON (((18.9169 51.0961, 18.9168 51.09...
    # Name: 0, dtype: object
    #
    # Geobounds: (18.035, 49.394, 19.974, 51.0994)
    geometry = models.JSONField(help_text="Full GeoJSON geometry (MULTIPOLYGON)")
    bounds = models.JSONField(help_text="Bounding box [minx, miny, maxx, maxy]")

    # analysis config
    model_path = models.CharField(max_length=500)
    config = models.JSONField(default=dict, help_text="Analysis parameters")
    zoom = models.IntegerField(default=8)
    original_image_path = models.CharField(max_length=500, help_text="Extracted tiles stitched")
    cropped_image_path = models.CharField(max_length=500, help_text="Cropped to województwo shape")
    mask_path = models.CharField(max_length=500, null=True, blank=True)
    fig_path = models.CharField(max_length=500, null=True, blank=True)

    # stats
    stats = models.JSONField(default=dict, help_text="Normalized stats")
    stats_json = models.CharField(max_length=500, null=True, blank=True)
    metadata_json = models.CharField(max_length=500, null=True, blank=True)
    change_log_path = models.CharField(max_length=500, null=True, blank=True)
    total_area_km2 = models.FloatField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # basic cache
    cache_key = models.CharField(max_length=255, db_index=True, unique=True)

    class Meta:
        ordering = ['wojewodztwo_name']
        indexes = [
            models.Index(fields=['wojewodztwo_id']),
            models.Index(fields=['wojewodztwo_name']),
        ]

    def __str__(self):
        return f"{self.wojewodztwo_name} (ID: {self.wojewodztwo_id})"