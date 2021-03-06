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
                'LICENSE': 'PRIVATE! Diese Leistungskennlinien dürfen nur innerhalb des deutschen Umweltbundesamtes (UBA) für Forschungszwecke verwendet werden.'
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

        attrs = {'describtion': "interpolated Leistungskennlinie",
                'creation_date': datetime.date.today(), 
                'author': 'Claudius Wehner',
                'contact-mail': 'Claudius.Wehner@uba.de',
                'LICENSE': 'PRIVATE! Diese Leistungskennlinien dürfen nur innerhalb des deutschen Umweltbundesamtes (UBA) für Forschungszwecke verwendet werden.'
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


def create_lkl_from_xls (
    xls_path: str,
    output_path: str = "/home/eouser/Documents/code/Windatlas/windatlas/anemos_data/wea_data/data/wea_lkl.nc",
    increment_wspd: float = 0.001,
    increment_rho: float = 0.0001,
    power_limiter: bool = True,
    wspd_to_zero: bool = True,
    append: bool = False,
    ):
    """_summary_

    Args:
        xls_path (str): _description_
        output_path (str, optional): _description_. Defaults to "/home/eouser/Documents/code/Windatlas/windatlas/anemos_data/wea_data/data/wea_lkl.nc".
        increment_wspd (float, optional): _description_. Defaults to 0.001.
        increment_rho (float, optional): _description_. Defaults to 0.0001.
        power_limiter (bool, optional): _description_. Defaults to True.
        wspd_to_zero (bool, optional): _description_. Defaults to True.
    """

    # 1. Reading the xls sheets to single pandas.Dataframes for each Leistungskennlinie (lkl)
    xls = pandas.ExcelFile(xls_path, engine="xlrd")
    sheets = xls.sheet_names

    lkl_dict = dict()

    for sheet in sheets:
        lkl_dict[sheet] = pandas.read_excel(xls, sheet, index_col=0)
    #return lkl_dict
    # 2. Extend all lkl's which are only for one air_density (rho=1.225) to multiple air_densitys based on the passed WEA_beispiel
    for key in lkl_dict:
        # check if initial lkl has only a single column and needs to be expanded from 1D to 2D
        if len(lkl_dict[key].columns) > 1:
            
            if key == 'WEA_beispiel':
                continue
            
            # extend lkl for abschaltzeiten bis wspd 35 
            index = lkl_dict[key].index
            wspd_step = numpy.gradient(index)[-1] # .median()
            wspd_max = index.max()
            rho_columns = lkl_dict[key].columns
            df_append = pandas.DataFrame(0,index=numpy.arange(wspd_max + wspd_step,35 + wspd_step,wspd_step), columns=rho_columns)
            lkl_dict[key] = pandas.concat([lkl_dict[key], df_append])

        else:
            lkl_dict[key] = create_lkl_from_1D_data(target_lkl=lkl_dict[key])
    #return lkl_dict
    # 3. Building a xarray.Dataarray for each lkl from the pandas.Dataframes
    for key in lkl_dict:
        
        coords = {
                "wspd": (["wspd"], numpy.array(lkl_dict[key].index, dtype="float64")),
                "rho": (["rho"], numpy.array(lkl_dict[key].columns, dtype="float64")),
                }

        attrs = {'describtion': "interpolated Leistungskennlinie",
                'creation_date': str(datetime.date.today()), 
                'author': 'Claudius Wehner',
                'contact-mail': 'Claudius.Wehner@uba.de',
                'LICENSE': 'PRIVATE! Diese Leistungskennlinien dürfen nur innerhalb des deutschen Umweltbundesamtes (UBA) für Forschungszwecke verwendet werden.'
                }

        
        array = xarray.DataArray(
            data=numpy.array(lkl_dict[key]),
            coords=coords,
            attrs=attrs
            )

        if not numpy.array_equal(array.wspd.to_numpy(), numpy.arange(3,35.5,0.5)) and not numpy.array_equal(array.rho.to_numpy(), numpy.arange(0.95,1.3,0.25)):
            wspd = numpy.arange(3,35.5,0.5)
            rho = numpy.arange(0.95,1.3,0.025)
            # coords = {"wspd":wspd,"rho":rho}
            array = array.interp(wspd=wspd, rho=rho, method="linear", kwargs=dict(fill_value="extrapolate"))
            array = array.where(array > 0, 0)

        # Extend right rho range from 1.275 to 1.3
        array = array.interp(rho = numpy.arange(0.95,1.325,0.025), method="linear", kwargs=dict(fill_value="extrapolate"))
        array = array.assign_coords(
                    coords={
                        "wspd": array.wspd.round(decimals=3),
                        "rho": array.rho.round(decimals=4)}
                )

        lkl_dict[key] = array
        del(array)

    #return lkl_dict
    # 4. Interpolate each lkl to the passed new increment
    for key in lkl_dict:
        new_wspd = numpy.arange(lkl_dict[key].wspd[0], lkl_dict[key].wspd[-1]+increment_wspd, increment_wspd, dtype=numpy.float64)
        new_rho = numpy.arange(lkl_dict[key].rho[0], lkl_dict[key].rho[-1]+increment_rho, increment_rho, dtype=numpy.float64)
        interpolated_array = lkl_dict[key].interp(wspd=new_wspd, rho=new_rho, method="quadratic")

        #### GOLDEN STEP TO MAKE xarray.Dataarray.sel() WORK AFTER INTERPOLATION ####
        # Reassigning helps solving the rounding error of estimation in float number
        interpolated_array = interpolated_array.assign_coords(
                    coords={
                        "wspd": interpolated_array.wspd.round(decimals=3),
                        "rho": interpolated_array.rho.round(decimals=4)}
                )
        #############################################################

        # 5. Limit power to maximum of not interpolated array, since the interpolation can in some cases lead to exceeding values
        if power_limiter:
            maxOriginalPower = lkl_dict[key].max()
            interpolated_array = interpolated_array.where(interpolated_array < maxOriginalPower, other = maxOriginalPower)
            interpolated_array = interpolated_array.where(interpolated_array > 0, other = 0)

        # 6. Extend Windspeed scale of lkl from the min (most of the time 3.5 m/s) to 0
        if wspd_to_zero:
            min_wspd_data = float(interpolated_array.wspd.min())

            zero_wspd = numpy.arange(0, min_wspd_data, increment_wspd, dtype=numpy.float64)
            zero_rho = interpolated_array.rho.values

            coords = {
                    "wspd": (["wspd"], zero_wspd),
                    "rho": (["rho"], zero_rho),
                    }

            zero_array = xarray.DataArray(
                data=numpy.zeros((zero_wspd.size, zero_rho.size)),
                coords=coords,
                attrs=None
            )

            interpolated_array = xarray.combine_by_coords([zero_array, interpolated_array])
            interpolated_array = interpolated_array.assign_coords(
                    coords={
                        "wspd": interpolated_array.wspd.round(decimals=3),
                        "rho": interpolated_array.rho.round(decimals=4)}
                )
            
        interpolated_array = interpolated_array.where(interpolated_array.rho <= 1.3, drop=True)
        lkl_dict[key] = interpolated_array.rename("power")
        del(interpolated_array)
    #return lkl_dict

    # 7. Concatinating interpolated lkl arrays
    concatinated_arrays = xarray.concat(lkl_dict.values(), pandas.Index(lkl_dict.keys(), name="wea_type"))
    del(lkl_dict)
    # 8. Export the full lkl-DataArray to a netCDF file
    concatinated_arrays.to_netcdf(path = output_path, mode="w")

def create_lkl_from_1D_data (
    target_lkl: pandas.DataFrame,
    base_lkl_path: str = "/home/eouser/Documents/code/Windatlas/windatlas/anemos_data/wea_data/raw_data/WEA_beispiel.xls",
    ) -> pandas.DataFrame:

    base_lkl = pandas.read_excel(base_lkl_path, index_col=0)

    rel_bsp = pandas.DataFrame().reindex_like(base_lkl)
    initial = base_lkl.loc[:,1.225]

    for column in base_lkl.columns:
        rel_bsp[column] = 1 + ((base_lkl[column] - initial)/initial)

    full_target_lkl = pandas.DataFrame().reindex_like(base_lkl)

    for column in full_target_lkl.columns:
        full_target_lkl[column] = target_lkl[1.225] * rel_bsp[column]
        full_target_lkl.loc[target_lkl.index.max() + 0.5,column] = 0
        full_target_lkl[column] = full_target_lkl[column].interpolate()

    return full_target_lkl.round()#, rel_bsp
