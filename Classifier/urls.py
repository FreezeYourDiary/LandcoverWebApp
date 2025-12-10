from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views
urlpatterns = [
    path('analyze-bbox/', views.analyze_bbox, name='analyze_bbox'),
    path('', views.map_page, name='map_page'),
    path('tiles/<int:z>/<int:x>/<int:y>.jpg', views.tile_from_mbtiles, name='tile'),
    # path('analyze_area/', views.analyze_area, name='analyze_area'),
    # path('city/<str:city_name>/', views.city, name='city_statistics'),
    path("analysis/<int:analysis_id>/stats/", views.get_analysis_stats, name="get_analysis_stats"),
    path("city_tiles/<str:city>/<int:z>/<int:x>/<int:y>.jpg", views.city_tile_from_mbtiles, name="city_tile"),

    # newwww
    path('wojewodztwa/', views.wojewodztwa_list_view, name='wojewodztwa_list'),
    path('wojewodztwo/<int:wojewodztwo_id>/', views.wojewodztwo_detail_view, name='wojewodztwo_detail'),
      # Województwa API endpoints
    path('api/wojewodztwa/', views.api_list_wojewodztwa, name='api_list_wojewodztwa'),
    path('api/analyze-wojewodztwo/', views.analyze_wojewodztwo, name='analyze_wojewodztwo'),
      # Województwa tiles
    path('wojewodztwo_tiles/<int:wojewodztwo_id>/<int:z>/<int:x>/<int:y>.jpg',
           views.wojewodztwo_tiles,
           name='wojewodztwo_tiles'),
    path('history/', views.history, name='history'),
    path('analysis-preview/<str:analysis_type>/<int:analysis_id>/',
           views.get_analysis_preview,
           name='analysis_preview'),
    path('download-analysis/<str:analysis_type>/<int:analysis_id>/<str:file_type>/',
           views.download_analysis_file,
           name='download_analysis_file'),
    path('wojewodztwo/<int:analysis_id>/download/<str:image_type>/', views.download_wojewodztwo_image,
                 name='download_wojewodztwo_image'),
    # path('wojewodztwo/<str:wojewodztwo_name>/', views.analyze_wojewodztwo, name='analyze_wojewodztwo'),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)