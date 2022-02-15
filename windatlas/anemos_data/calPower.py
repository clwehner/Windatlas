from enum import Enum
import datetime
from typing import List, Dict, Optional

import numpy
import xarray

from weaPoints import WeaPoints


class PowerCalculationMethod(Enum):
    TSNC3KM = "TSNC3km"
    NC3KM = "NC3km"
    #MEAN90MEAN = "90mean"
    MEAN90WEIBULL = "90weibull"
    MEAN90RAYLEIGH = "90rayleigh"
    MEAN3WEIBULL = "3weibull"
    MEAN3RAYLEIGH = "3rayleigh"


class Get_Power():
    def __init__(self,
            point_list:WeaPoints,
            data_type:PowerCalculationMethod,
            time_frame:List[int] = [2009, 2018],
        ):
        self.point_list = point_list
        self.data_type = data_type

        self.time_frame = [self.transforme_date(date) if not isinstance(date, numpy.datetime64) else date for date in time_frame]
        
        if any ([self.time_frame[0]<numpy.datetime64("2009-01-01"),self.time_frame[-1]>numpy.datetime64("2018-01-01")]):
            raise ValueError("Input dates for time_frame must be in range of: '2009-01-01' to '2018-01-01'")

        print("Passed time_frame valid!")

    def calculate_power(self, kind:PowerCalculationMethod):
        if kind.value == "TSNC3km":
            self.nc_power(data = "ts")
        if kind.value == "NC3km":
            self.nc_power(data = "nc")
        if kind.value == "90weibull":
            self.weibull_power(data = "90m")
        if kind.value == "3weibull":
            self.weibull_power(data = "3km")
        if kind.value == "90rayleigh":
            self.rayleigh_power(data = "90m")
        if kind.value == "3rayleigh":
            self.rayleigh_power(data = "3km")

    def transforme_date(self, date) -> numpy.datetime64:
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
            return numpy.datetime64(date)

        elif len(date)==7:
            # year and month given
            date_str = f"{date}-01"
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return numpy.datetime64(date)

        elif len(date)==10:
            # date given
            date =  datetime.datetime.strptime(date, "%Y-%m-%d") # "%Y-%m-%dT%H:%M:%S.%fZ"
            return numpy.datetime64(date)

        else:
            raise ValueError("Input dates for time_frame must be string in the form of year-month-day like: '2012-11-23'")


class Get_power_tsnc():
    pass


class Get_power_weibull():
    def __init__():
        pass

    def weibull(self, v_i:numpy.array, A:float, k:float) -> numpy.array:
        return 1 - numpy.exp(-(v_i/A)**k)

    def rayleigh(self, v_i:numpy.array, v_mean:float) -> numpy.array:
        return 1 - numpy.exp(-(numpy.pi/4)*(v_i/v_mean)**2)

    def aep(self, F:numpy.array, P:numpy.array, s:float=0.85) -> float:
        AEP_list = list()
        for i, _ in enumerate(F):
            if i == 0:
                AEP_i = 8760 * F[i] * P[i]

            else:
                AEP_i = 8760 * (F[i] - F[i-1]) * ((P[i] + P[i-1])/2)
            
            AEP_list.append(AEP_i)

        return sum(AEP_list) * s

    
    def weibull_aep(self, lkl:xarray.DataArray, A:float, k:float, rho:float, s:float=0.85) -> float:
        F = self.weibull(v_i=lkl.wspd.to_numpy(), A=A, k=k)
        P = lkl.interp(rho=rho, method="linear").to_numpy()

        return self.aep(F=F, P=P, s=s)

    def rayleigh_aep(self, lkl:xarray.DataArray, v_mean:float, rho:float, s:float=0.85) -> float:
        F = self.rayleigh(v_i=lkl.wspd.to_numpy(), v_mean=v_mean)
        P = lkl.interp(rho=rho, method="linear").to_numpy()

        return self.aep(F=F, P=P, s=s)

        