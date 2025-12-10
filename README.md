# My Map Analysis Tool
Analyze map areas with CNN-based land cover classification.

![woj.png](screenshots/woj.png)

[Release Notes](RELEASE.md) for details.

# Local Build & Setup Guide

1. Clone the repository  
2. Create and activate a virtual environment
   python -m venv venv
   source venv/bin/activate
3. pip install -r [requirements.txt](requirements.txt)
4. python manage.py migrate
5. python manage.py runserver

## To run locally

To run app (tiles for analysis), **`.mbtiles` format**.:
- stitch and crop satellite tiles  
- generate map layers  
- render imagery on the Leaflet map  

Place `.mbtiles` file inside LandCoverWebApp/data/raw

## Requirements
developed with
- dataset: https://github.com/phelber/EuroSAT?tab=readme-ov-file
- python 3.12
- Django 5.2.7: https://www.djangoproject.com/
- leaflet.js: https://leafletjs.com/
- Polish geojson borders: https://github.com/ppatrzyk/polska-geojson 
 


