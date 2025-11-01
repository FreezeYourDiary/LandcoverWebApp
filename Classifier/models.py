# Create your models here.
from django.db import models

class TileSource(models.Model):
    """Optional: store MBTiles / tile source metadata"""
    name = models.CharField(max_length=100)
    path = models.CharField(max_length=1024)  #  path ~~URL
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Analysis(models.Model):
    """A single analysis run (cached)."""
    created_at = models.DateTimeField(auto_now_add=True)

    image_path = models.CharField(max_length=1024)   # src image
    model_path = models.CharField(max_length=1024)
    config = models.JSONField()   # basic tile_size, smoothing, etc
    stats = models.JSONField(null=True, blank=True)
    metadata_json = models.CharField(max_length=1024, blank=True, null=True)  # path to metadata json
    stats_json = models.CharField(max_length=1024, blank=True, null=True)
    fig_path = models.CharField(max_length=1024, blank=True, null=True)
    mask_path = models.CharField(max_length=1024, blank=True, null=True)
    change_log_path = models.CharField(max_length=1024, blank=True, null=True)
    # bbox in lon/lat:  left, bottom, right, top
    bbox_minx = models.FloatField(null=True, blank=True)
    bbox_miny = models.FloatField(null=True, blank=True)
    bbox_maxx = models.FloatField(null=True, blank=True)
    bbox_maxy = models.FloatField(null=True, blank=True)

    #? caching lookups
    cache_key = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return f"Analysis {self.id} {self.created_at.isoformat()}"
