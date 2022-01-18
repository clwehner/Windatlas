import numpy as np
import matplotlib.pyplot as plt
import xarray
import psycopg2 # for postgresSQL management
from dataclasses import dataclass

from enum import Enum, unique

#########################################################
### Filter functions to work through netCDF wind data ###
#########################################################

@unique
class ProjectionTransformation(Enum):
    PYPROJ = "pyproj"
    GDAL = "gdal"

@dataclass
class Point():
    coor:list(float,float)
    level:int

    def __post_init__(self):
        self.xy = self.coor_transformation(coor=self.coor)

    def coor_transformation(
            coor:list,
            engine:ProjectionTransformation=ProjectionTransformation.PYPROJ
            )->list:
        """[summary]

        Args:
            coor (list): [description]
            engine (ProjectionTransformation, optional): [description]. Defaults to ProjectionTransformation.PYPROJ.

        Returns:
            list: [description]
        """
        __lambert_proj_str = "+proj=lcc +lat_1=48.0 +lat_2=54.0 +lat_0=50.893 +lon_0=10.736 +a=6370000 +b=6370000 +nadgrids=null +no_defs"

        if engine.value == "pyproj":
            from pyproj import CRS, Transformer

            crsD3E5 = CRS.from_proj4(__lambert_proj_str)
            crsGeo = CRS.from_epsg(4326)
            geo2altas = Transformer.from_crs(crsGeo, crsD3E5)

            x,y = geo2altas.transform(coor[0], coor[1])
            return[x,y]

        if engine == "gdal":
            from ogr import Geometry, wkbPoint
            from osr import SpatialReference
            
            d3e5Prj = SpatialReference()
            d3e5Prj.ImportFromProj4(__lambert_proj_str)
            geoPrj = SpatialReference()
            geoPrj.ImportFromEPSG(4326)

            point = Geometry(wkbPoint)
            point.AddPoint(coor[0], coor[1])
            point.AssignSpatialReference(geoPrj)    # tell the point what coordinates it's in
            point.TransformTo(d3e5Prj)              # project it to the out spatial reference
            return[point.GetX(),point.GetY()]

#@dataclass
class CoordinateSearch ():
    def __init__(self, xarray:xarray.Dataset, Point:dict):
        self.data = xarray
        self.point = Point

    def searchPoint(self):
        self.coordinate, self.level = self.findPoint(
            xarrayData = self.data, 
            Point = self.point)

    def findPoint(self, xarrayData:xarray.Dataset, Point:dict):
        """
        Findes the closest lon, lat coordiante to a given Point in a xarray Dataset, where lon, lat is given as a value in dependency to the coordinates x, y.

        """
        abslat = np.abs(xarrayData.lat-Point["coor"][0])
        abslon = np.abs(xarrayData.lon-Point["coor"][1])
        c = np.maximum(abslon, abslat)
        
        if 'level' in xarrayData.dims and 'level' in Point.keys():
            abslev = np.abs(xarrayData.level-Point["level"])
            nearestlevel = np.where(abslev == np.min(abslev))
            nearestlevel = xarrayData.level[nearestlevel]
            return np.where(c == np.min(c)), nearestlevel
        
        return np.where(c == np.min(c)), None

    def getPointData(self, xarrayData:xarray.Dataset, x, y, level=None, time=None):
        """
        Selects point in a given xarray with the supplied x, y local coordinates. 
        If a certain level of hight is passed as well, the time will be filtered as well.
        """
        if level:
            return xarrayData.sel(x=x, y=y, level=level)
        
        return xarrayData.sel(x=x, y=y)

    def coor_transformation(coor:list,engine:ProjectionTransformation=ProjectionTransformation.PYPROJ)->list:
        __lambert_proj_str = "+proj=lcc +lat_1=48.0 +lat_2=54.0 +lat_0=50.893 +lon_0=10.736 +a=6370000 +b=6370000 +nadgrids=null +no_defs"

        if engine.value == "pyproj":
            from pyproj import CRS, Transformer

            crsD3E5 = CRS.from_proj4(__lambert_proj_str)
            crsGeo = CRS.from_epsg(4326)
            geo2altas = Transformer.from_crs(crsGeo, crsD3E5)

            x,y = geo2altas.transform(coor[0], coor[1])
            return[x,y]

        if engine == "gdal":
            from ogr import Geometry, wkbPoint
            from osr import SpatialReference
            
            d3e5Prj = SpatialReference()
            d3e5Prj.ImportFromProj4(__lambert_proj_str)
            geoPrj = SpatialReference()
            geoPrj.ImportFromEPSG(4326)

            point = Geometry(wkbPoint)
            point.AddPoint(coor[0], coor[1])
            point.AssignSpatialReference(geoPrj)    # tell the point what coordinates it's in
            point.TransformTo(d3e5Prj)              # project it to the out spatial reference
            return[point.GetX(),point.GetY()]


##########################################################################
### Plot functions to display "Windrosen" based on agregated wind data ###
##########################################################################

def circularHisto(xarray:xarray.core.dataset.Dataset, dataVariable:str, grid:bool=False):
    '''
    To Do's:
    - Add colorbar
    '''
    radii = xarray[dataVariable].values
    N = radii.size
    theta = np.linspace(0.0, 2 * np.pi, N, endpoint=False)
    width = np.full((1, 12), 2 * np.pi / 13)[0]
    
    fig= plt.figure()
    ax = fig.add_subplot(111, projection='polar')
    bars = ax.bar(theta, radii, bottom=0.0, width=width)
    # Use custom colors and opacity
    for r, bar in zip(radii, bars):
        bar.set_facecolor(plt.cm.viridis(r / radii.max()))
        bar.set_alpha(0.7)

    ax.set_theta_zero_location("N")
    if grid:
        ax.set_rticks(np.arange(0,radii.max(),2))
    else:
        ax.set_rticks([])
    
    ticks = ["N","NW","W","SW","S","SE","E","NE"]
    ax.set_xticklabels(ticks)
    
    if dataVariable == "wspd":
        ax.set_title("Average Windspeed [m/s] 2008 - 2017", pad=25)
        
    if dataVariable == "histo":
        ax.set_title("Distribution of wind directions 2008 - 2017", pad=25)
    #fig.show()

    return fig

    
def describingHisto(xarray):
    fig, axs = plt.subplots(1, 2)
    
    diags =("histo","wspd")
    
    for num, ax in enumerate(axs):
        ax = circularHisto(xarray, dataVariable=diags[num])


### MATPLOTLIB TO DASH

from io import BytesIO
import base64

def fig_to_uri(in_fig, close_all=True, **save_args):
    """
    Save a figure as a URI
    :param in_fig:
    :return:
    """
    out_img = BytesIO()
    in_fig.savefig(out_img, format='png', **save_args)
    if close_all:
        in_fig.clf()
        plt.close('all')
    out_img.seek(0)  # rewind file
    encoded = base64.b64encode(out_img.read()).decode("ascii").replace("\n", "")
    return "data:image/png;base64,{}".format(encoded)