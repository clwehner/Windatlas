import numpy
import pandas
import xarray
import datetime
import os

#import matplotlib.pyplot as plt

from enum import Enum,unique
from typing import Optional, List

@unique
class XarrayDataType(Enum):
    DATAARRAY= "DataArray"
    DATASET= "Dataset"

@unique
class SelectMethod(Enum):
    NEAREST = "nearest"
    LINEAR = "linear"
    QUDRATIC = "quadratic"
    CUBIC = "cubic"

class Lkl_array():
    """[summary]

    Returns:
        [type]: [description]
    """
    def __init__(
        self,
        source_csv: str,
        xr_dataclass: Optional[XarrayDataType] = XarrayDataType.DATAARRAY,
        interpolated: Optional[bool] = False,
        power_limiter: Optional[bool] = False,
        #lkl_xarray = None,
        ):
        self.xr_dataclass = xr_dataclass
        self.interpolated = interpolated
        self.power_limiter = power_limiter

        self.lkl_pandas = self.__lkl_to_pandas(source_csv=source_csv)
        if self.xr_dataclass.value == "DataArray":
            self.lkl_xarray = self.__lkl_to_xarrayDataArray()
        if self.xr_dataclass.value == "Dataset":
            self.lkl_xarray = self.__lkl_to_xarrayDataset()

    def __lkl_to_pandas(
        self,
        source_csv,
        ):
        """[summary]
        """
        csv_2D_data = pandas.read_csv(source_csv, sep=';', header=0, index_col=0).dropna()
        # sorting the columns in case they where unsorted
        return csv_2D_data.reindex(sorted(csv_2D_data.columns), axis=1)

    def __lkl_to_xarrayDataset(self):
        """[summary]
        """
        data_vars={'leistung':(['wspd','rho'], numpy.array(self.lkl_pandas), 
                        {'units': 'kW',
                        'long_name': 'Die Leistungskurve einer Windkraftanlage ist eine Kurve, die anzeigt, wie hoch die abgegebene elektrische Leistung in Abhängigkeit der Windgeschwindigkeit und der Luftdichte ist.'
                        ,}),
                    }

        coords = {
                "wspd": (["wspd"], numpy.array(self.lkl_pandas.index, dtype="float64")),
                "rho": (["rho"], numpy.array(self.lkl_pandas.columns, dtype="float64")),
                }

        attrs = {'describtion': "interpolated Leistungskennlinie",
                'creation_date': datetime.date.today(), 
                'author': 'Claudius Wehner',
                'contact-mail': 'Claudius.Wehner@uba.de',
                'LICENSE': 'Diese Leistungskennlinien dürfen nur innerhalb des UBA für Forschungszwecke verwendet werden.'
                }

        return xarray.Dataset(
            data_vars=data_vars,
            coords=coords,
            attrs=attrs
        )

    def __lkl_to_xarrayDataArray(self):
        """[summary]
        """
        coords = {
                "wspd": (["wspd"], numpy.array(self.lkl_pandas.index, dtype="float64")),
                "rho": (["rho"], numpy.array(self.lkl_pandas.columns, dtype="float64")),
                }

        attrs = {'describtion':"interpolated Leistungskennlinie",
                'creation_date':str(datetime.date.today()), 
                'author':'Claudius Wehner',
                }

        return xarray.DataArray(
            data=numpy.array(self.lkl_pandas),
            coords=coords,
            attrs=attrs
        )

    def lkl_interpolate(
            self,
            increment_wspd: float,
            increment_rho: float,
            power_limiter: Optional[bool] = True,
            to_zero: Optional[bool] = True):
        """[summary]

        Args:
            increment_wspd (float): [description]
            increment_rho (float): [description]
            power_limiter (bool, optional): [description]. Defaults to True.
        """
        new_wspd = numpy.arange(self.lkl_xarray.wspd[0], self.lkl_xarray.wspd[-1]+increment_wspd, increment_wspd, dtype=numpy.float64)
        new_rho = numpy.arange(self.lkl_xarray.rho[0], self.lkl_xarray.rho[-1]+increment_rho, increment_rho, dtype=numpy.float64)

        testarray2Di = self.lkl_xarray.interp(wspd=new_wspd, rho=new_rho, method="cubic")

        #### GOLDEN STEP TO MAKE .sel() WORK AFTER INTERPOLATION ####
        # Reassigning helps solving the rounding error
        self.lkl_xarray = testarray2Di.assign_coords(
                    coords={
                        "wspd": testarray2Di.wspd.round(decimals=3),
                        "rho": testarray2Di.rho.round(decimals=4)}
                )
        #############################################################
        if power_limiter:
            maxOriginalPower = self.lkl_xarray.max()
            self.lkl_xarray = self.lkl_xarray.where(self.lkl_xarray < maxOriginalPower, other = maxOriginalPower)
            self.lkl_xarray = self.lkl_xarray.where(self.lkl_xarray > 0, other = 0)
            self.power_limiter: bool = True

        if to_zero:
            self.lkl_xarray = self.wspd_to_zero()
        
        self.interpolated = True

    def wspd_to_zero (
        self,
        increment_wspd: Optional[float] = None,
        ) -> xarray.DataArray:
        """Power curves deliverd by the manufacturers do not include wind speeds dwn to 0, but to different low non-zero values.
        In order to respond to wind speeds inside the anemos data which are between zero and the minimum delivered wind speed
        value, this function adds a zero matrix to fill the gap. This matrix is based on the given wind speed increment in the 
        current power curve, as well as the minimum wind speed value and the air density dimension values.  

        Args:
            increment_wspd (Optional[float], optional): Increment of wind speed from zero to current wspd.min . Defaults to None.

        Returns:
            xarray.DataArray: An updated power curve will be returned, where wind speeds are filled to zero by a given or initial increment.
        """
        # set increment based on data
        if not increment_wspd:
            increment_wspd = float(self.lkl_xarray.wspd[1] - self.lkl_xarray.wspd[0])

        min_wspd_data = float(self.lkl_xarray.wspd.min())

        zero_wspd = numpy.arange(0, min_wspd_data, increment_wspd, dtype=numpy.float64)
        zero_rho = self.lkl_xarray.rho.values

        coords = {
                "wspd": (["wspd"], zero_wspd),
                "rho": (["rho"], zero_rho),
                }

        zero_array = xarray.DataArray(
            data=numpy.zeros((zero_wspd.size, zero_rho.size)),
            coords=coords,
            attrs=None
        )
        
        return xarray.combine_by_coords([zero_array, self.lkl_xarray])
        
    def get_power(
            self,
            wspd: numpy.ndarray,
            rho: numpy.ndarray,
            sel_method: Optional[SelectMethod] = SelectMethod.NEAREST
            ) -> xarray.DataArray:
        """[summary]

        Args:
            wspd (numpy.ndarray): [description]
            rho (numpy.ndarray): [description]
            sel_method ([type], optional): [description]. Defaults to None.

        Returns:
            xarray.DataArray: [description]
        """
        #### GOLDEN STEP ####
        data = self.lkl_xarray.sel(
                wspd=xarray.DataArray(wspd, dims='wea'), 
                rho=xarray.DataArray(rho, dims='wea'), 
                method=sel_method.value)# if error appears, use method="nearest"
        #####################

        return data

    def to_netcdf(
        self,
        path: str,
        name_if_dataarray: Optional[str] = None
        ):
        
        try:
            os.remove(path)
        except OSError:
            pass

        if self.xr_dataclass.value == "DataArray":
            export = self.lkl_xarray.to_dataset(name=name_if_dataarray, promote_attrs=True)
            export.to_netcdf(path=path, mode="w")


def create_lkl_from_1D_data (
    base_lkl: pandas.DataFrame,
    target_lkl: pandas.DataFrame,
    ) -> pandas.DataFrame:

    rel_bsp = pandas.DataFrame().reindex_like(base_lkl)
    initial = base_lkl.loc[:,1.225]

    for column in base_lkl.columns:
        rel_bsp[column] = 1 + ((base_lkl[column] - initial)/initial)

    full_target_lkl = pandas.DataFrame().reindex_like(base_lkl)

    for column in full_target_lkl.columns:
        full_target_lkl[column] = target_lkl[1.225] * rel_bsp[column]

    return full_target_lkl.round()
