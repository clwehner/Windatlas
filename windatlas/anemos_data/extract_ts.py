from dataclasses import dataclass
from enum import Enum

# Imports for coordinate transformation
from pyproj import CRS, Transformer
from ogr import Geometry, wkbPoint
from osr import SpatialReference

import pandas
import os

class CoordTrasformation(Enum):
    PYPROJ="pyproj"
    GDAL="gdal"

class WindData(Enum):
    WINDSPEED = "wspd"
    AIRDENSITY = "roh"
    RELATIVEAIRHUMIDITY = "rhum"
    WINDDIRECTION = "wdir"
    AIRPRESSURE = "pres"
    WEIBULLA = "wbA"
    WEIBULLK = "wbk"

class WindDataType(Enum):
    TSNETCDF = "TSNC-Format/"
    NETCDF = "NC-Format/"
    MEAN90M = "3arcsecs/"
    MEAN3KM = "Statistics/"

@dataclass
class Wind_data():
    wind_data: WindData
    wind_data_type: WindDataType = WindDataType.TSNETCDF
    chunks: dict = None
    mfdataset: bool = False
    parallel: bool = True
    _xy_coord_path: str = r"./development/xy_lamber_projection_values"
    _wind_data_path: str = r"/uba/anemos_winddata/20191029_anemosDataFull/UBA-Windatlas/"

    def __post_init__(self):
        self.__build_data_path()
        self.__load_winddata
        self._assign_new_lambert_coor()

    def __build_data_path(self):

        self.data_path = self._wind_data_path + self.wind_data_type.value


    def __load_winddata(self):
        pass

    def _assign_new_lambert_coor(
            self,
            xy_path:str = None
            ):
        
        if not xy_path:
            xy_path = self._xy_coord_path

        new_dim_coor = pandas.read_csv(xy_path)
        # assign the new x,y values to the netCDF data
        x = new_dim_coor["x"].dropna().astype("int").values
        y = new_dim_coor["y"].values

        self.xarray_data = self.xarray_data.assign_coords(
            coords={"x": x,"y": y}
            )

@dataclass
class Point_query():
    coord: list(float,float)
    __lambert_proj_str: str = "+proj=lcc +lat_1=48.0 +lat_2=54.0 +lat_0=50.893 +lon_0=10.736 +a=6370000 +b=6370000 +nadgrids=null +no_defs"
     
    def __post_init__(self):
        self.xy_coord = self.__coor_transformation(self.coord)

    def __coor_transformation(
            self,
            coor: list,
            engine: CoordTrasformation = CoordTrasformation.PYPROJ
            )->list:

        if engine.value == "pyproj":
            crsD3E5 = CRS.from_proj4(self.__lambert_proj_str)
            crsGeo = CRS.from_epsg(4326)
            geo2altas = Transformer.from_crs(crsGeo, crsD3E5)

            x,y = geo2altas.transform(coor[0], coor[1])
            return[x,y]

        if engine.value == "gdal":
            d3e5Prj = SpatialReference()
            d3e5Prj.ImportFromProj4(self.__lambert_proj_str)
            geoPrj = SpatialReference()
            geoPrj.ImportFromEPSG(4326)

            point = Geometry(wkbPoint)
            point.AddPoint(coor[0], coor[1])
            point.AssignSpatialReference(geoPrj)    # tell the point what coordinates it's in
            point.TransformTo(d3e5Prj)              # project it to the out spatial reference
            return[point.GetX(),point.GetY()]

    def point_search(
            self,

            ):
        pass

    def time_series_extraction(
            self
            ):
        pass





@dataclass
class Point_collection():
    pass

