import numpy
import pandas
import xarray
import datetime

#import matplotlib.pyplot as plt

from dataclasses import dataclass
from enum import Enum

class XarrayDataType(Enum):
    DATAARRAY= "DataArray"
    DATASET= "Dataset"

@dataclass
class Lkl_array ():
    """[summary]

    Returns:
        [type]: [description]
    """
    source_csv: str 
    xr_dataclass: XarrayDataType = XarrayDataType.DATAARRAY
    interpolated: bool = False
    power_limiter: bool = False


    def __post_init__(self):
        self.__lkl_to_pandas()
        if self.xr_dataclass.value == "DataArray":
            self.__lkl_to_xarrayDataArray()
        if self.xr_dataclass.value == "Dataset":
            self.__lkl_to_xarrayDataset()

    def __lkl_to_pandas(self):
        """[summary]
        """
        csv_2D_data = pandas.read_csv(self.source_csv, sep=';', header=0, index_col=0).dropna()
        # sorting the columns in case they where unsorted
        self.lkl_pandas = csv_2D_data.reindex(sorted(csv_2D_data.columns), axis=1)


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

        self.lkl_xarray = xarray.Dataset(
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
                'creation_date':datetime.date.today(), 
                'author':'Claudius Wehner',
                }

        self.lkl_xarray = xarray.DataArray(
            data=numpy.array(self.lkl_pandas),
            coords=coords,
            attrs=attrs
        )

    def lkl_interpolate(
            self,
            increment_wspd:float,
            increment_rho:float,
            power_limiter = True):
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
        testarray2Di = testarray2Di.assign_coords(
                    coords={
                        "wspd": testarray2Di.wspd.round(decimals=3),
                        "rho": testarray2Di.rho.round(decimals=4)}
                )
        #############################################################
        if power_limiter:
            maxOriginalPower = self.lkl_xarray.max()
            testarray2Di = testarray2Di.where(testarray2Di < maxOriginalPower, other = maxOriginalPower)
            self.power_limiter: bool = True
        
        self.interpolated = True
        self.lkl_xarray =testarray2Di

    def wspd_to_zero ():
        pass
        
    def get_power(
            self,
            wspd: numpy.ndarray,
            rho: numpy.ndarray,
            sel_method = None) -> xarray.DataArray:
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
                wspd=xarray.DataArray(wspd, dims='z'), 
                rho=xarray.DataArray(rho, dims='z'), 
                method=sel_method)# if error appears, use method="nearest"
        #####################

        return data
