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
