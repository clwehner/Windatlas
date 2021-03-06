from datetime import datetime
import math
import numpy as np
import matplotlib.pyplot as plt
import xarray
import pandas
import datetime

# for Coordinate Transformation
from pyproj import CRS, Transformer
from ogr import Geometry, wkbPoint
from osr import SpatialReference

# for function definitions
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import List, Dict, Optional

from anemosData import _WindData, WindDataKind, TsNcWindData, Mean90mWindData, Mean3km10aWindData
#from power_curve import Lkl_array

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

class WindDataType(Enum):
    TSNETCDF = r"TSNC-Format/"
    NETCDF = r"NC-Format/"
    MEAN90M = r"3arcsecs/"
    MEAN3KM10A = r"Statistics/10-Jahresmittel/"
    MEAN3KM1A = r"Statistics/Jahresmittel/"

class CalculationMethod (Enum):
    WEIBULL = "weibull"
    RAYLEIGH = "rayleigh"
    WINDSPEEDMEAN = "wspd"

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
    wea_type: Optional[str]=field(
            default=None, 
            compare=False)
    x_y_coor: List[float]=field(init=False)
    transform_engine: Optional[ProjectionTransformation]=field(
            default=ProjectionTransformation.PYPROJ,
            repr=False,
            compare=False)
    interpolation_method: Optional[InterpolationMethod]=field(
            default=InterpolationMethod.LINEAR,
            repr=False,
            compare=False)
    power_time_series: xarray.DataArray=field(
            default=None, 
            init=False, 
            repr=False,
            compare=False)
    EinheitMastrNummer: Optional[str]=None
    Hauptwindrichtung: Optional[int]=None
    mittlere_windgeschw_Hauptwindrichtung: Optional[float]=None

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

    def get_tsnetcdf_power_output(
        self,
        wind_data: dict,
        power_curves: xarray.Dataset,
        #wind_params: Optional[List[WindDataKind]] = [WindDataKind.WINDSPEED, WindDataKind.AIRDENSITY],
        save_to: Optional[str] = None,
        ):
        """TO DO: Include time step factor for power calculation relative to data!!!

        Args:
            wind_data (dict): _description_
            power_curves (xarray.DataArray): _description_
            save_to (Optional[str], optional): _description_. Defaults to None.
        """
        # resetting the whole wind data in the passed wind_data dict to the desired point time series
        interp_wind_data = {}
        for key, value in wind_data.items():
            interp_wind_data[key] = value.interp_point(
                        target_coord=self.x_y_coor,
                        target_level=self.level, 
                        method=self.interpolation_method)#.load()

        # calculating power from wspd, rho and power_curve
        #print(power_curves)
        power_curve = power_curves.sel(wea_type=self.wea_type)
        #print(power_curve.values)
        power = power_curve.load().sel(
                wspd=xarray.DataArray(interp_wind_data["wspd"].wspd.to_numpy(), dims='wea'), 
                rho=xarray.DataArray(interp_wind_data["rho"].rho.to_numpy(), dims='wea'), 
                method="nearest")#.load()

        #df = power.to_pandas().to_frame()
        #df = df.rename({0: "Eout"}, axis=1)
        #df = df.set_index(new_wind_data["wspd"].time.values)
        #print(power.wea)
        #print(type(power))
        self.power_time_series = power.power.values / 6 # divided by 4 because 10 min resolution


    def get_mean90m_power_output(
        self,
        wind_data: dict,
        power_curves: xarray.DataArray,
        calculation_method: CalculationMethod,
        ):
        
        # resetting the whole wind data in the passed wind_data dict to the desired point time series
        interp_wind_data = {}
        for key, value in wind_data.items():

            interp_wind_data[key] = value.interp_point(
                        target_coord=self.lat_lon_coor,
                        target_level=self.level, 
                        method=self.interpolation_method)#.load()

        # calculating power from wspd, rho and power_curve
        power_curve = power_curves.sel(wea_type=self.wea_type)

        if calculation_method is CalculationMethod.WEIBULL:
            self.power_time_series = self.weibull_aep(
                lkl=power_curve,
                A=float(interp_wind_data["wbA"].wbA.to_numpy()),
                k=float(interp_wind_data["wbk"].wbk.to_numpy()),
                rho=float(interp_wind_data["rho"].rho.to_numpy()),
                years = 10,
                s = 1,
                )

        if calculation_method is CalculationMethod.RAYLEIGH:
            self.power_time_series = self.rayleigh_aep(
                lkl=power_curve,
                v_mean=float(interp_wind_data["wspd"].wspd.to_numpy()),
                rho=float(interp_wind_data["rho"].rho.to_numpy()),
                years = 10,
                s = 1,
                )

    def get_mean3km10a_power_output(
        self,
        wind_data: dict,
        power_curves: xarray.DataArray,
        calculation_method: CalculationMethod,
        ):
        
        # resetting the whole wind data in the passed wind_data dict to the desired point time series
        interp_wind_data = {}
        for key, value in wind_data.items():

            interp_wind_data[key] = value.interp_point(
                        target_coord=self.x_y_coor,
                        target_level=self.level, 
                        method=self.interpolation_method)#.load()

        # calculating power from wspd, rho and power_curve
        power_curve = power_curves[self.wea_type]

        if calculation_method is CalculationMethod.WEIBULL:
            print(interp_wind_data["rho"].rho)
            self.power_time_series = self.weibull_aep(
                lkl=power_curve,
                A=float(interp_wind_data["wbA"].wbA.to_numpy()),
                k=float(interp_wind_data["wbk"].wbk.to_numpy()),
                rho=float(interp_wind_data["rho"].rho.to_numpy()),
                years = 10,
                s = 1,
                )

        if calculation_method is CalculationMethod.RAYLEIGH:
            self.power_time_series = self.rayleigh_aep(
                lkl=power_curve,
                v_mean=float(interp_wind_data["wspd"].wspd.to_numpy()),
                rho=float(interp_wind_data["rho"].rho.to_numpy()),
                years = 10,
                s = 1,
                )


    def rayleigh (
        self, 
        v_i:np.array, 
        v_mean:float
        ) -> np.array:
        """_summary_

        Args:
            v_i (np.array): _description_
            v_mean (float): _description_

        Returns:
            np.array: _description_
        """

        return 1 - np.exp(-(np.pi/4)*(v_i/v_mean)**2)

    def weibull (
        self,
        v_i:np.array, 
        A:float, 
        k:float
        ) -> np.array:
        """_summary_

        Args:
            v_i (np.array): _description_
            A (float): _description_
            k (float): _description_

        Returns:
            np.array: _description_
        """

        return 1 - np.exp(-(v_i/A)**k)

    def annual_energy_production (
        self, 
        F:np.array,
        P:np.array, 
        s:float=0.85
        ) -> float:
        """_summary_

        Args:
            F (np.array): _description_
            P (np.array): _description_
            s (float, optional): _description_. Defaults to 0.85.

        Returns:
            float: _description_
        """

        AEP_list = list()
        for i, _ in enumerate(F):
            if i == 0:
                AEP_i = 8760 * F[i] * P[i]

            else:
                AEP_i = 8760 * (F[i] - F[i-1]) * ((P[i] + P[i-1])/2)
            
            AEP_list.append(AEP_i)

        return sum(AEP_list) * s

    def weibull_aep(
        self, 
        lkl:xarray.DataArray, 
        A:float, 
        k:float, 
        rho:float, 
        years:int, 
        s:float=0.85
        ) -> float:
        """_summary_

        Args:
            lkl (xarray.DataArray): _description_
            A (float): _description_
            k (float): _description_
            rho (float): _description_
            years (int): _description_
            s (float, optional): _description_. Defaults to 0.85.

        Returns:
            float: _description_
        """

        F = self.weibull(v_i=lkl.wspd.to_numpy(), A=A, k=k)
        #print(lkl)
        P = lkl.interp(rho=rho, method="linear").power.to_numpy()

        return self.annual_energy_production(F=F, P=P, s=s) * years

    def rayleigh_aep(
        self, 
        lkl:xarray.DataArray, 
        v_mean:float, 
        rho:float, 
        years:int, 
        s:float=0.85
        ) -> float:
        """_summary_

        Args:
            lkl (xarray.DataArray): _description_
            v_mean (float): _description_
            rho (float): _description_
            years (int): _description_
            s (float, optional): _description_. Defaults to 0.85.

        Returns:
            float: _description_
        """
        
        F = self.rayleigh(v_i=lkl.wspd.to_numpy(), v_mean=v_mean)
        P = lkl.interp(rho=rho, method="linear").power.to_numpy()

        return self.annual_energy_production(F=F, P=P, s=s) * years

    def __nth_nearest_1D (self,sorted_array, value, n):
        closesed = list()
        diff = abs(sorted_array - value)

        for i in range(0,n,1):
            arg_nth_min_in_diff = np.where(diff == np.partition(diff, i)[i])
            int_of_nth_value = int(sorted_array[arg_nth_min_in_diff][0])
            closesed.append(int_of_nth_value)

        return closesed

    def calculate_Hauptwindrichtung (self):
        levels = np.array([40,60,80,100,120,140,170,200,250,300])
        levels = self.__nth_nearest_1D(sorted_array=levels, value=self.level, n=2)
        Hauptwindrichtung = list()
        mittlere_windgeschw_Hauptwindrichtung = list()

        for level in levels:
            data = Mean3km10aWindData(wind_data_kind=WindDataKind.DIRHISTOS, level=level)
            data = data.winddata.interp(x= self.x_y_coor[0], y= self.x_y_coor[1], method= "quadratic")
            mean_wspd_per_direction = data.wspd.values
            wspd_histo = data.histo.values
            directions = data.klassengrenzen.values - data.klassengrenzen.values[1]
            hauptwindID = np.argmax(wspd_histo)

            Hauptwindrichtung.append(directions[hauptwindID])
            mittlere_windgeschw_Hauptwindrichtung.append(mean_wspd_per_direction[hauptwindID])

        self.Hauptwindrichtung = sum(Hauptwindrichtung) / len(Hauptwindrichtung)

        # Not working jet
        #self.mittlere_windgeschw_Hauptwindrichtung = sum(mittlere_windgeschw_Hauptwindrichtung) / len(mittlere_windgeschw_Hauptwindrichtung)




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

    time = None
    time_frame = None

    def __init__(
            self, 
            lat_lon_coor: List[List[float]],
            level: List[float],
            wea_types: Optional[List[str]] = None,
            interpolation_method: Optional[List[InterpolationMethod]] = None,
            #point_list: List[_WeaPoint] = None,
            #num_Points:int = None,
            _xy_coord_path: str = r"./lambert_projection/xy_lamber_projection_values",
            _interpolated_power_curves: bool = True,
            ):

        self._xy_coord_path = _xy_coord_path
        self._interpolated_power_curves = _interpolated_power_curves

        if not wea_types:
            wea_types = [None] * len(lat_lon_coor)

        if len(lat_lon_coor) == len(level) == len(wea_types):
            if not interpolation_method:
                self.point_list = [_WeaPoint(point, level, typ) for point, level, typ in zip(lat_lon_coor, level, wea_types)]
            if interpolation_method:
                self.point_list = [_WeaPoint(point, level, typ, interpolation_method = intm) for point, level, typ, intm in zip(lat_lon_coor, level, wea_types, interpolation_method)]
        
        self.num_Points = len(self.point_list)

    def transforme_date(self, date) -> np.datetime64:
        """Date input must be either an integer year like `2009`
        or a string in the shape of `year-month-day` like `2009-12-24`

        Args:
            date ([type]): must be either an integer year like `2009`
        or a string in the shape of `year-month-day` like `2009-12-24`

        Raises:
            ValueError: [description]

        Returns:
            numpy.datetime64: [description]
        """
        date = str(date)
        if len(date)==4:
            # Year given
            date_str = f"{date}-01-01"
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return np.datetime64(date)

        elif len(date)==7:
            # year and month given
            date_str = f"{date}-01"
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return np.datetime64(date)

        elif len(date)==10:
            # date given
            date =  datetime.datetime.strptime(date, "%Y-%m-%d") # "%Y-%m-%dT%H:%M:%S.%fZ"
            return np.datetime64(date)

        else:
            raise ValueError("Input dates for time_frame must be string in the form of year-month-day like: '2012-11-23'")
    
    def get_windpower_out(
        self,
        wind_data_type: WindDataType,
        time_frame:List[int] = [2009, 2018],
        calculation_method: CalculationMethod = CalculationMethod.WEIBULL,
        ):

        self.time_frame = [self.transforme_date(date) if not isinstance(date, np.datetime64) else date for date in time_frame]

        if any ([self.time_frame[0]<np.datetime64("2009-01-01"),self.time_frame[-1]>np.datetime64("2018-12-31")]):
            raise ValueError("Input dates for time_frame must be in range of: '2009-01-01' to '2018-12-31'")

        print("Passed time_frame valid.")

        if wind_data_type is WindDataType.TSNETCDF:
            self.__tsnetcdf_out()

        elif wind_data_type is WindDataType.NETCDF:
            pass

        elif wind_data_type is WindDataType.MEAN3KM10A:
            self.time_frame = [np.datetime64("2009-01-01"), np.datetime64("2018-12-31")]
            self.__mean3km10a_out(calculation_method=calculation_method)

        elif wind_data_type is WindDataType.MEAN90M:
            self.time_frame = [np.datetime64("2009-01-01"), np.datetime64("2018-12-31")]
            self.__mean90m_out(calculation_method=calculation_method)
        
        else:
            pass#print("")

    def calculate_Hauptwindrichtung (self):
        for point in self.point_list:
            point.calculate_Hauptwindrichtung()

    def _load_power_curves(
        self,
        ):

        if self._interpolated_power_curves:
            path = "/uba/anemos_winddata/powercurves/single_netcdfs/wea_*.nc"
            power_curves = xarray.open_mfdataset(path, parallel=True, engine="h5netcdf", combine="nested", concat_dim="wea_type")

        if not self._interpolated_power_curves:
            path = "/home/eouser/Documents/code/Windatlas/windatlas/anemos_data/wea_data/example/WEA_beispiel.csv"
            power_curve = pandas.read_csv(path, delimiter=";", index_col=0)
            power_curve = power_curve.reindex(sorted(power_curve.columns), axis=1)

            power_curve = xarray.DataArray(power_curve).rename({"dim_0":"wspd", "dim_1":"rho"})
            power_curve = power_curve.assign_coords(rho=np.float64(power_curve.rho))
            power_curves = power_curve.to_dataset(name="test_wea")


        return power_curves

    def __tsnetcdf_out(
        self,
        wind_params: Optional[List[WindDataKind]] = [WindDataKind.WINDSPEED, WindDataKind.AIRDENSITY]
        ):

        self.wind_data = {}
        for param in wind_params:
            self.wind_data[param.value] = TsNcWindData(wind_data_kind=param, time_frame=self.time_frame)
        print("TSnetCDF data loaded.")

        self.time_periode = list(self.wind_data.values())[0].winddata.time.to_numpy()
        print("Time period loaded.")

        power_curves = self._load_power_curves()

        for num, point in enumerate(self.point_list):
            point.get_tsnetcdf_power_output(
                wind_data=self.wind_data, 
                power_curves=power_curves,
                )
            print(f"Windpower turbine {num+1} complete")

    def __mean90m_out(
        self,
        calculation_method: CalculationMethod,
        ):
        
        if calculation_method is CalculationMethod.WEIBULL:
            wind_params = [WindDataKind.AIRDENSITY, WindDataKind.WEIBULLA, WindDataKind.WEIBULLK]

        if calculation_method is (CalculationMethod.RAYLEIGH or CalculationMethod.WINDSPEEDMEAN):
            wind_params = [WindDataKind.AIRDENSITY, WindDataKind.WINDSPEED]

        self.time_periode = [np.datetime64("2018-12-31")]

        self.wind_data = {}
        for param in wind_params:
            self.wind_data[param.value] = Mean90mWindData(wind_data_kind=param)
        print("mean90m data loaded.")

        power_curves = self._load_power_curves()

        for num, point in enumerate(self.point_list):
            point.get_mean90m_power_output(
                wind_data=self.wind_data, 
                power_curves=power_curves,
                calculation_method = calculation_method,
                )
            print(f"Windpower turbine {num+1} complete")

    def __mean3km10a_out(
        self,
        calculation_method: CalculationMethod,
        ):
        
        if calculation_method is CalculationMethod.WEIBULL:
            wind_params = [WindDataKind.AIRDENSITY, WindDataKind.WEIBULLA, WindDataKind.WEIBULLK]

        if calculation_method is (CalculationMethod.RAYLEIGH or CalculationMethod.WINDSPEEDMEAN):
            wind_params = [WindDataKind.AIRDENSITY, WindDataKind.WINDSPEED]

        self.time_periode = [np.datetime64("2018-12-31")]

        self.wind_data = {}
        for param in wind_params:
            self.wind_data[param.value] = Mean3km10aWindData(wind_data_kind=param)
        print("mean3km10a data loaded.")

        power_curves = self._load_power_curves()

        for num, point in enumerate(self.point_list):
            point.get_mean3km10a_power_output(
                wind_data=self.wind_data, 
                power_curves=power_curves,
                calculation_method=calculation_method,
                )
            print(f"Windpower turbine {num+1} complete")

    def timeseries_to_pandas (self) -> pandas.DataFrame:

        Eout = {}
        for num, point in enumerate(self.point_list):
            Eout[f"wea_{num+1}: {point.lat_lon_coor}"] = point.power_time_series

        return pandas.DataFrame(data=Eout,index=self.time_periode)





def from_MaStR(
        mastr_df: pandas.DataFrame,
        time_frame: List[int] = [2009, 2018],
        path_powercurves: Optional[str] = r"./wea_data/example/test_wea.nc",
    ) -> pandas.DataFrame:
    # extract needed data from mastr df
    lat_lon_coor = None
    level = None
    weaType = None
    mastrID = None

    # open Leistungskennlinien
    power_curves = xarray.open_dataset(path_powercurves)

    # build wea_point list
    weaPoints = WeaPoints(
        lat_lon_coor = lat_lon_coor,
        level = level,
        wea_types = weaType,#["test_wea"] * size,
        #interpolation_method = [InterpolationMethod.LINEAR] * size,
    )

    # calculate Eout
    weaPoints.get_power_output(power_curves=power_curves, time_frame=time_frame)

    # Build time series Dataframe
    Eout = {}
    for num, point in enumerate(weaPoints.point_list):
        Eout[f"wea_{num+1}: {point.lat_lon_coor}"] = point.power_time_series

    return pandas.DataFrame(data=Eout,index=weaPoints.time)

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