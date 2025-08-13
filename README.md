# Raster Tools QGIS Plugin
## About
This QQGIS plugin provides two tools:
1. Lazy Raster Calculator: This raster calculator allows you to perform arithmetic on raster layers with lazy computation. Lazy computation means the result will not be computed until you need it. 
2. Delivered Cost: Calculate timber harvesting and hauling costs using raster-based cost surfaces.

### Features
- Lazy evaluation of rasters
- Raster arithmetic operations
- Raster data type and CRS transformation
- Delivered cost analysis using an area of interest and facility locations
- Export results as new raster layers

## Installation
This plugin requires the folowing python modules: raster_tools, osmnx, and py3dep. The best way to install these into the QGIS environment will depend on your operating system:
### Windows
1. Install QGIS through OSGeo4W Network Installer. You can find the download/instructions at this link: https://qgis.org/download/.
2. Open QGIS and it's python console. In the python console type: 
`import numpy`
`print(numpy.__version__)`
3. Open the OSGeo4W Shell and type the following commands:
`pip install raster_tools osmnx py3dep numpy=={your numpy version in QGIS}`
4. Download the zip file from this repository. Then in QGIS open the plugins menu from the top and select 'Manage and Install Plugins. Select 'Install from zip' and select the zip file from this repo.

### Linux/Mac
Linux and Mac require QGIS to be installed through the conda-forge channel for this plugin to work. To acess conda-forge you must first install Miniconda by following the instructions at this link: https://www.anaconda.com/docs/getting-started/miniconda/install
1. Once you have Miniconda installed, in your terminal/command prompt enter the following commands:
`conda config --add channels conda-forge`
`conda config --set channel-priority strict`
`conda update --all`
2. If preferred you can create a conda environment for you QGIS to be installed in. To do this enter this into your terminal/command prompt:
`conda create --name qgis-env`
You can replace 'qgis-env' with any name you'd like. Next enter:
`conda activate qgis-env'
3. Install QGIS via conda-forge. Enter this command into your terminal/command prompt:
`conda install conda-forge::qgis`
4. To open your newly installed QGIS simply type `qgis` in the conda environemnt you ran the install command from.
5. Install the following dependencies in the conda environment using the following command:
`pip install raster-tools osmnx py3dep`
6. Download the zip file from this repository. Then in QGIS open the plugins menu from the top and select 'Manage and Install Plugins. Select 'Install from zip' and select the zip file from this repo.

## Usage
### Lazy Raster Calculator

![Lazy Raster Calculator UI](media/rCalcUI.png)
#### Expressions
In order to use the calculator widget you must first load one or more rasters into QGIS. These rasters will automatically show up under 'Raster Layers' in the dockwidget, from here you can double click the raster to insert it into the expression box and form the expression you wish to evaluate. If an expression is invalid it will notify you of this below the expression box.
![Invalid Expression](media/invalidEx.png)
The calculator provides the following operators: 
- Arithmetic operators: addition +, subtraction -, multiplication *, division /, exponents **, and parentheses ( ).
- Logical operators: less than <, greater than >, less than or equal too <=, greater than or equal too >=, not equal too !=, and equal too ==. These will return a raster of boolean values.
- Bitwise operators: and &, or |, not ~. The input rasters must be of type int for these operators.

#### Result Layer Options
![Result Layer Options](media/resultLayer.png)
##### CRS
As you can see you have a couple of options for the resulting layer from your expression. The first one being the CRS of the resulting layer. You can choose from EPSG:4326 or the project CRS by using the drop down button. You may also select the button to the right of the combo box which will open the QGIS dialogue for CRS selection. Additionally you can type the CRS into the box, but it must be in authid format, for example "EPSG:4326".

##### Data Type
You can choose what data type the resulting raster will be outputted as, or you may let raster_tools handle the data type. 

The following data types are included:
![Data types](media/dtypes.png)

##### Lazy Layer Checkbox
![Lazy Layer Checkbox](media/lazyLayerBox.png)
When the lazy layer checkbox is **checked** and the 'Okay' button is clicked with a valid expression you will be prompted for a name for the lazy raster. After entering a name, a placeholder layer will be added to the QGIS layer panel with '(Lazy)' following the name you inputted as shown here: ![Lazy Layer in Layer Panel](media/lazyLayer.png) You may notice that nothing shows up in the map extent of QGIS or that the new layer has an unavailable layer icon next to it's name, this is because the raster has not been calculated yet. From here you can either force computation or use the lazy layer in another expression. To force computation right-click on the lazy layer and choose one of the options as shown below:
![Context Menu for lazy layers](media/computeLayer.png)
The 'Compute Lazy Layer' option will force computation of the raster and place it into the QGIS layer panel. 'Compute and Export Lazy Layer...' will force computation and then prompt you for a location to save it too, avoiding loading it into QGIS altogether. After you choose one of these options the lazy layer will be removed from the layer panel and you will no longer be able to use it.
If you leave the checkbox **unchecked** then the expression will be evaluated immediately, you will be prompted for a name for the layer, and the resulting layer will be added to the QGIS layer panel. This is only a **temporary layer**, meaning that you must save the raster to a location on your computer, otherwise it will be lost once QGIS is closed.
