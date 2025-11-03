from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views
urlpatterns = [
    path('analyze-bbox/', views.analyze_bbox, name='analyze_bbox'),
    path('', views.map_page, name='map_page'),
    path('tiles/<int:z>/<int:x>/<int:y>.jpg', views.tile_from_mbtiles, name='tile'),
    # path('analyze_area/', views.analyze_area, name='analyze_area'),
    path('city/<str:city_name>/', views.city, name='city_statistics'),
    path("analysis/<int:analysis_id>/stats/", views.get_analysis_stats, name="get_analysis_stats"),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)