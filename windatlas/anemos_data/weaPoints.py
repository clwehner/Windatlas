import numpy as np
import matplotlib.pyplot as plt
import xarray
import pandas

# for Coordinate Transformation
from pyproj import CRS, Transformer
from ogr import Geometry, wkbPoint
from osr import SpatialReference

# for function definitions
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import List, Dict, Optional

from anemosData import _WindData, WindDataKind, TsNcWindData
from power_curve import Lkl_array

#########################################################
### Filter functions to work through netCDF wind data ###
#########################################################

# Defining Enums
@unique
class ProjectionTransformation(Enum):
    PYPROJ = "pyproj"
    GDAL = "gdal"

@unique
class InterpolationMethod(Enum):
    NEAREST = "nearest"
    LINEAR = "linear"
    QUDRATIC = "quadratic"
    CUBIC = "cubic"

# 
@dataclass()
class _WeaPoint():
    """This is a dataclass for wind turbine points.

    Instances of this class are ment for extractions of wind turbine power output on the bases of anemos wind data and wind turbine types. 

    The coordinates passed (`lat_lon_coor`) should be inside the anemos wind data region. 

    If for the passed `wea_type` exists a performance curve, a power output can later be calculated.

    Args:
        lat_lon_coor (List[float, float]): A list of two float values latitude and longitude.
        level (float): A float value representing the hub hight of the represented wind turbine.
        wea_type (Optional[str]): A string with a valid manufacturer and unit name.
        x_y_coor (List[float]): A list of x and y coordinates which are calculated for the anemos windatlas data by a given lamber projection transformation.
        transform_engine (Optional[ProjectionTransformation]): Definition of the python framework to use for the coordinate transformation.
        interpolation_method (Optional[InterpolationMethod]): Interpolation method to be used in later data extraction processes, if the lat_lon_coor is located in between grid points of the anemos windatlas data.
    """
    lat_lon_coor: List[float]
    level: float
    wea_type: Optional[str] = field(
            default=None, 
            compare=False)
    x_y_coor: List[float] = field(init=False)
    transform_engine: Optional[ProjectionTransformation] = field(
            default=ProjectionTransformation.PYPROJ,
            repr=False,
            compare=False)
    interpolation_method: Optional[InterpolationMethod] = field(
            default=InterpolationMethod.LINEAR,
            repr=False,
            compare=False)
    power_time_series: xarray.DataArray = field(
            default = None, 
            init = False, 
            repr=False,
            compare = False)

    def __post_init__(self):
        self.x_y_coor = self.__coor_transformation()

    def __coor_transformation(self) -> List[float]:
        """Transforms lat lon coordinates to a local lambert projection coordinate(x,y) given by anemos for their windatlas data.
        """
        __lambert_proj_str = "+proj=lcc +lat_1=48.0 +lat_2=54.0 +lat_0=50.893 +lon_0=10.736 +a=6370000 +b=6370000 +nadgrids=null +no_defs"

        if self.transform_engine.value == "pyproj":

            crsD3E5 = CRS.from_proj4(__lambert_proj_str)
            crsGeo = CRS.from_epsg(4326)
            geo2altas = Transformer.from_crs(crsGeo, crsD3E5)

            x,y = geo2altas.transform(self.lat_lon_coor[0], self.lat_lon_coor[1])
            return [x,y]

        if self.transform_engine.value == "gdal":
            
            d3e5Prj = SpatialReference()
            d3e5Prj.ImportFromProj4(__lambert_proj_str)
            geoPrj = SpatialReference()
            geoPrj.ImportFromEPSG(4326)

            point = Geometry(wkbPoint)
            point.AddPoint(self.lat_lon_coor[0], self.lat_lon_coor[1])
            point.AssignSpatialReference(geoPrj)    # tell the point what coordinates it's in
            point.TransformTo(d3e5Prj)              # project it to the out spatial reference
            return [point.GetX(),point.GetY()]

    def get_power_output(
        self,
        wind_data: dict,
        power_curve: xarray.DataArray,
        save_to: Optional[str] = None,
        ):

        # resetting the whole wind data in the passed wind_data dict to the desired point time series
        print(f"{wind_data.items()}")
        new_wind_data = {}
        for key, value in wind_data.items():
            print(f"{value.wind_data_kind}")
            new_wind_data[key] = value.interp_point(
                        target_coord=self.x_y_coor,
                        target_level=self.level, 
                        method=self.interpolation_method)

        # calculating power from wspd, rho and power_curve
        power = power_curve.sel(
                wspd=xarray.DataArray(new_wind_data["wspd"].wspd.values, dims='wea'), 
                rho=xarray.DataArray(new_wind_data["rho"].rho.values, dims='wea'), 
                method="nearest")

        df = power.to_pandas().to_frame()
        df = df.rename({0: "Eout"}, axis=1)
        df = df.set_index(new_wind_data["wspd"].time.values)

        self.power_time_series = df


class WeaPoints():
    """This is a collection class for the _Wea_point class.

    Instances of this class are ment for extractions of wind turbine power output on the bases of anemos wind data and wind turbine types. 

    The coordinates passed (`lat_lon_coor`) should be inside the anemos wind data region. 

    If for the passed `wea_type` exists a performance curve, a power output can later be calculated.

    Args:
        lat_lon_coor (List[float, float]): A list of two float values latitude and longitude.
        level (float): A float value representing the hub hight of the represented wind turbine.
        wea_type (Optional[str]): A string with a valid manufacturer and unit name.
        interpolation_method (Optional[InterpolationMethod]): Interpolation method to be used in later data extraction processes, if the lat_lon_coor is located in between grid points of the anemos windatlas data.
    """
    def __init__(
            self, 
            lat_lon_coor: List[List[float]],
            level: List[float],
            wea_types: Optional[List[str]] = None,
            interpolation_method: Optional[List[InterpolationMethod]] = None,
            #point_list: List[_WeaPoint] = None,
            #num_Points:int = None,
            _xy_coord_path: str = r"./lambert_projection/xy_lamber_projection_values",
            ):

        self._xy_coord_path = _xy_coord_path

        if not wea_types:
            wea_types = [None] * len(lat_lon_coor)

        if len(lat_lon_coor) == len(level) == len(wea_types):
            if not interpolation_method:
                self.point_list = [_WeaPoint(point, level, typ) for point, level, typ in zip(lat_lon_coor, level, wea_types)]
            if interpolation_method:
                self.point_list = [_WeaPoint(point, level, typ, interpolation_method = intm) for point, level, typ, intm in zip(lat_lon_coor, level, wea_types, interpolation_method)]
        
        self.num_Points = len(self.point_list)

    def _load_new_lambert_coor(
            self,
            xy_path: Optional[str] = None,
            ):
        
        if not xy_path:
            xy_path = self._xy_coord_path

        new_dim_coor = pandas.read_csv(xy_path)
        # assign the new x,y values to the netCDF data
        x = new_dim_coor["x"].dropna().astype("int").values
        y = new_dim_coor["y"].values
        return [x, y]


    def get_power_output(
            self,
            power_curves: xarray.Dataset,
            wind_params: Optional[List[WindDataKind]] = [WindDataKind.WINDSPEED, WindDataKind.AIRDENSITY],
        ):
        # Transformation data for windatlas
        #transformation = self._load_new_lambert_coor()

        wind_data = {}
        for param in wind_params:
            wind_data[param.value] = TsNcWindData(wind_data_kind=param)#, xy_coord=transformation)

        for point in self.point_list:
            power_curve_wea = power_curves[point.wea_type]
            point.get_power_output(wind_data=wind_data, power_curve=power_curve_wea)

    


##########################################################################
### Plot functions to display "Windrosen" based on agregated wind data ###
##########################################################################

def _circularHisto(xarray:xarray.Dataset, dataVariable:str, grid:bool=False):
    """[summary]

    Args:
        xarray (xarray.Dataset): [description]
        dataVariable (str): [description]
        grid (bool, optional): [description]. Defaults to False.

    Returns:
        [type]: [description]
    """
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

    
def _describingHisto(xarray):
    fig, axs = plt.subplots(1, 2)
    
    diags =("histo","wspd")
    
    for num, ax in enumerate(axs):
        ax = _circularHisto(xarray, dataVariable=diags[num])


### MATPLOTLIB TO DASH

from io import BytesIO
import base64

def _fig_to_uri(in_fig, close_all=True, **save_args):
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