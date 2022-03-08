#from dataclasses import dataclass
from enum import (
                Enum,
                unique,
                )

from typing import (
                Optional, 
                Dict, 
                List,
                )

from abc import (
                ABC, 
                abstractmethod,
                )

from multiprocessing import (
                Pool,
                cpu_count,
                )
#import concurrent

import pandas
#import numpy
import xarray
#import geopandas
#import rioxarray
#from shapely.geometry import mapping

CPUTOUSE = cpu_count() - 1

class WindDataKind(Enum):
    WINDSPEED = "wspd"
    AIRDENSITY = "rho"
    RELATIVEAIRHUMIDITY = "rhum"
    WINDDIRECTION = "wdir"
    AIRPRESSURE = "pres"
    WEIBULLA = "wbA"
    WEIBULLK = "wbk"

class WindDataType(Enum):
    TSNETCDF = r"TSNC-Format/"
    NETCDF = r"NC-Format/"
    MEAN90M = r"3arcsecs/"
    MEAN3KM = r"Statistics/"

@unique
class InterpolationMethod(Enum):
    NEAREST = "nearest"
    LINEAR = "linear"
    QUDRATIC = "quadratic"
    CUBIC = "cubic"

class AggregationMethod(Enum):
    MEAN = "mean"
    MEDIAN = "median"
    MAX = "max"
    MIN = "min"


class _WindData(ABC):
    """To Do:
    - exclude x, y transform to only load them ones before processing netCDF data
    """

    _wind_data_path = r"/uba/anemos_winddata/20191029_anemosDataFull/UBA-Windatlas"
    winddata = None

    def __init__(
        self,
        _wind_data_type: WindDataType = None,
        _wind_data_path: Optional[str] = None,
        ):

        if _wind_data_path:
            self._wind_data_path = _wind_data_path
        self._wind_data_type = _wind_data_type

        self.data_path = self.__build_data_path()

    def __build_data_path(self) -> str:
        return f"{self._wind_data_path}/{self._wind_data_type.value}"

    @abstractmethod
    def load_winddata(self):
        pass

    @abstractmethod
    def interp_point(
        self,
        target_coord: List[float],
        interpolation_method: Optional[InterpolationMethod] = InterpolationMethod.LINEAR,
        ) -> xarray.Dataset:
        pass

    @abstractmethod
    def agg_shape(
        self,
        target_shapes: List[float],
        aggregation_method: Optional[AggregationMethod] = AggregationMethod.MEDIAN,
        interpolation_method: Optional[InterpolationMethod] = InterpolationMethod.LINEAR,
        ) -> xarray.Dataset:
        pass


class TsNcWindData(_WindData):

    _xy_coord_path = r"./lambert_projection/xy_lamber_projection_values"
    _wind_data_type = WindDataType.TSNETCDF
    winddata = None

    def __init__(
        self,
        wind_data_kind: WindDataKind,
        time_frame: Optional[List[int]] = None,
        _wind_data_path: Optional[str] = None,
        chunks: Optional[Dict] = None,
        mfdataset: Optional[bool] = True,
        parallel: Optional[bool] = True,
        ):

        super().__init__( 
            _wind_data_path = _wind_data_path,
            _wind_data_type = self._wind_data_type,
            )#_WindData, self

        self.time_frame = time_frame
        self.wind_data_kind = wind_data_kind

        self.chunks = chunks
        self.mfdataset = mfdataset
        self.parallel = parallel

        self.winddata = self.load_winddata()

    def _assign_new_lambert_coor(
            self,
            xarray_data:xarray.Dataset,
            xy_path: Optional[str] = None,
            ):

        if not xy_path:
            xy_path = self._xy_coord_path

        new_dim_coor = pandas.read_csv(xy_path)
        # assign the new x,y values to the netCDF data
        x = new_dim_coor["x"].dropna().astype("int").values
        y = new_dim_coor["y"].values

        return xarray_data.assign_coords(
            coords={"x": x,"y": y}
            )
        
    def __load_winddata_ds(self) -> List[xarray.Dataset]:
        """ToDo: 
        - specify date to year for import and more specific date for .sel after concatenation

        Returns:
            List[xarray.Dataset]: [description]
        """
        data_list = []
        for year in range(self.time_frame[0], self.time_frame[1]+1, 1):
            path = f"{self.data_path}{self.wind_data_kind.value}.10L.{year}.ts.nc"
            data = xarray.open_dataset(path, engine='h5netcdf', chunks=self.chunks)
            data = self._assign_new_lambert_coor(data)
            data_list.append(data)

        return data_list

    def __load_winddata_mfds(self) -> xarray.Dataset:
        path = f"{self.data_path}{self.wind_data_kind.value}.10L.*.ts.nc"
        data = xarray.open_mfdataset(path, engine='h5netcdf', chunks=self.chunks, parallel=self.parallel)

        if self.time_frame:
            start = str(self.time_frame[0])
            end = str(self.time_frame[1])
            data = data.sel(time=slice(start, end))

        data = self._assign_new_lambert_coor(data)

        return data

    def load_winddata(self):
        if self.mfdataset:
            return self.__load_winddata_mfds()

        if not self.mfdataset:
            return self.__load_winddata_ds()

    def get_winddata(self):
        return self.winddata

    def interp_point(
        self,
        target_coord: List[float],
        target_level,
        method: Optional[InterpolationMethod] = InterpolationMethod.LINEAR,
        ) -> xarray.Dataset:

        x=target_coord[0]
        y=target_coord[1]
        level=target_level
        method=method.value

        if self.mfdataset:
            interp_data =  self.winddata.interp(
                    x=x,#[0],
                    y=y,#[0],
                    level=level,#[0],
                    method=method)#.interp(
                    #level=level[0],
                    #method=method)

            return interp_data#.load()
        
        if not self.mfdataset:

            global interp_year
            def interp_year(data, x=x, y=y, level=level, method=method):
                interp_data = data.interp(
                        x=x[0],
                        y=y[0],
                        level=level[0],
                        method=method).load()
                #print(f"{data.nbytes}, {x[0]}, {y[0]}, {level[0]}, {method}")
                return interp_data

            #with concurrent.futures.ProcessPoolExecutor() as executor:
            #    array = executor.map(interp_year(), self.winddata)
            
            with Pool(CPUTOUSE) as proc_pool:
                array = proc_pool.map(interp_year, self.winddata)
                proc_pool.close()
                proc_pool.join()

                ts_interp = xarray.concat(array, dim="time")

            return ts_interp.load()

    def agg_shape(
        self,
        target_shapes: List[float],
        aggregation_method: Optional[AggregationMethod] = AggregationMethod.MEDIAN,
        interpolation_method: Optional[InterpolationMethod] = InterpolationMethod.LINEAR,
        ) -> xarray.Dataset:
        pass
        # https://gis.stackexchange.com/questions/357490/mask-xarray-dataset-using-a-shapefile
        # https://gis.stackexchange.com/questions/354782/masking-netcdf-time-series-data-from-shapefile-using-python/354798#354798
        # https://pypi.org/project/xagg/

        #MSWEP_monthly2 = xarray.open_dataarray()
        #MSWEP_monthly2.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True)
        #MSWEP_monthly2.rio.write_crs("epsg:4326", inplace=True)
        #Africa_Shape = geopandas.read_file('D:\G3P\DATA\Shapefile\Africa_SHP\Africa.shp', crs="epsg:4326")
        # SHAPE COORDINATES NEED TO BE TRANSFORMED

        #clipped = MSWEP_monthly2.rio.clip(Africa_Shape.geometry.apply(mapping), Africa_Shape.crs, drop=False)


class Mean90mWindData(_WindData):

    _xy_coord_path = r"./lambert_projection/xy_lamber_projection_values"
    _wind_data_type = WindDataType.MEAN90M
    winddata = None

    def __init__(
        self,
        wind_data_kind: WindDataKind,
        #time_frame: Optional[List[int]] = None,
        _wind_data_path: Optional[str] = None,
        chunks: Optional[Dict] = None,
        mfdataset: Optional[bool] = False,
        parallel: Optional[bool] = True,
        ):

        super().__init__( 
            _wind_data_path = _wind_data_path,
            _wind_data_type = self._wind_data_type,
            )#_WindData, self

        #self.time_frame = time_frame
        self.wind_data_kind = wind_data_kind

        self.chunks = chunks
        self.mfdataset = mfdataset
        self.parallel = parallel

        self.winddata = self.load_winddata()


    def __load_winddata_mfds(self) -> xarray.Dataset:
        path = f"{self.data_path}D-3km.E5.3arcsecs.{self.wind_data_kind.value}*.nc"
        data = xarray.open_mfdataset(path, engine='h5netcdf', chunks=self.chunks, parallel=self.parallel)

        #data = self._assign_new_lambert_coor(data)

        return data

    def __load_winddata_ds(self) -> xarray.Dataset:
        path = f"{self.data_path}D-3km.E5.3arcsecs.{self.wind_data_kind.value}.2009-2018.nc"
        data = xarray.open_dataset(path, engine='h5netcdf')

        #data = self._assign_new_lambert_coor(data)

        return data

    def load_winddata(self) -> xarray.Dataset:
        if self.mfdataset:
            return self.__load_winddata_mfds()

        if not self.mfdataset:
            return self.__load_winddata_ds()

    def get_winddata(self):
        return self.winddata

    def interp_point(
        self,
        target_coord: List[float],
        target_level,
        method: Optional[InterpolationMethod] = InterpolationMethod.LINEAR,
        ) -> xarray.Dataset:

        x=target_coord[1],
        y=target_coord[0],
        level=target_level,
        method=method.value

        if not self.mfdataset:
            interp_data =  self.winddata.interp(
                    x=x[0],
                    y=y[0],
                    level=level[0],
                    method=method)#.interp(
                    #level=level[0],
                    #method=method)

            return interp_data#.load()
        
        if self.mfdataset:
            raise NotImplementedError()

    def agg_shape(
    self,
    target_shapes: List[float],
    aggregation_method: Optional[AggregationMethod] = AggregationMethod.MEDIAN,
    interpolation_method: Optional[InterpolationMethod] = InterpolationMethod.LINEAR,
    ) -> xarray.Dataset:
        pass