from dataclasses import dataclass
from enum import Enum

from weaPoints import _WeaPoint

import pandas
import numpy
import os

class WindDataKind(Enum):
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

class WindData():
    """To Do:
    - exclude x, y transform to only load them ones before processing netCDF data
    """
    def __init__(
        self,
        wind_data: WindDataKind,
        point: _WeaPoint,
        wind_data_type: WindDataType = WindDataType.TSNETCDF,
        chunks: dict = None,
        mfdataset: bool = False,
        parallel: bool = True,
        _xy_coord_path: str = r"./development/xy_lamber_projection_values",
        _wind_data_path: str = r"/uba/anemos_winddata/20191029_anemosDataFull/UBA-Windatlas/",
        ):

        self.data_path = self.__build_data_path()
        self.__load_winddata()
        self._assign_new_lambert_coor()

    def __build_data_path(self) -> str:
        return self._wind_data_path + self.wind_data_type.value

    def __load_winddata(self):
        pass

    def _assign_new_lambert_coor(
            self,
            xy_coord:numpy.ndarray,
            ):

        self.xarray_data = self.xarray_data.assign_coords(
            coords={"x": xy_coord[0],"y": xy_coord[1]}
            )