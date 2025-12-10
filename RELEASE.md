# LandCoverWebAoo release

## About
Application is aimed at analyzing various regions in Poland, specifically regarding land cover, 
utilizing data that have been processed by a neural network based on satellite imagery. 
Web app for analyzing selected areas on a map, including land cover statistics, overlay images, and visualizations.

## Features
- Select areas on a map and analyze land cover.
- Visualize results with overlay images and statistical charts.
- Export JSON stats.
## Model trained
A set of convolutional neural networks was used for general classification of satellite images.  
Selected neural networks (own CNN, Mobilenetv2) training, and evaluating individual models.
![accuracy_plot.png](screenshots/accuracy_plot.png) ![confusion_matrix.png](screenshots/confusion_matrix.png)
## LandcoverWebAppView

## Assets included
- `Classifier/inputs/networks/` – pre-trained neural networks
- `data/` – example image tiles / mbtiles
- `static`
  - `geodata`
  - `js/` – frontend logic
  - `css/` – styles
  - `.html` / Django templates – main UI


## Screenshots

### Map, UI
![ui.png](screenshots/ui.png)
Config & history with analysis panel
![ui2.png](screenshots/ui2.png)
### Statistics Panel
![stats.png](screenshots/stats.png)
### Analysis
![ui3.png](screenshots/ui3.png)
![woj.png](screenshots/woj.png)

## Assets