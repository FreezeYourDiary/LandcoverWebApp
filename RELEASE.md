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


<img src="screenshots/accuracy_plot.png" width="400" height="400" alt="accuracy.png">
<img src="screenshots/confusion_matrix.png" width="400" height="400" alt="confsion.png">


## LandcoverWebAppView

## Assets 
- `Classifier/inputs/networks/` – pre-trained neural networks
- `data/` – example image tiles / mbtiles
- `static`
  - `geodata`
  - `.js/` – frontend logic
  - `.css/` – styles
  - `.html` / Django templates – main UI


## Screenshots

### Map, UI
![ui.png](screenshots/ui.png)

### Config & History with Analysis Panel
<img src="screenshots/ui2.png" width="400" alt="ui2.png">
<img src="screenshots/history.png" width="400" alt="history.png">

### Statistics Panel
![stats.png](screenshots/stats.png)

### Analysis
![ui3.png](screenshots/ui3.png)
![woj.png](screenshots/woj.png)