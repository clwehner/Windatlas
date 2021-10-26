import numpy as np
import matplotlib.pyplot as plt
import xarray
import psycopg2 # for postgresSQL management

#########################################################
### Filter functions to work through netCDF wind data ###
#########################################################


class CoordinateSearch ():
    def __init__(self, xarray:xarray.core.dataset.Dataset, Point:dict):
        self.data = xarray
        self.point = Point

    def searchPoint(self):
        self.coordinate, self.level = self.findPoint(
            xarrayData = self.data, 
            Point = self.point)

    def findPoint(self, xarrayData:xarray.core.dataset.Dataset, Point:dict):
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

    def getPointData(self, xarrayData:xarray.core.dataset.Dataset, x, y, level=None, time=None):
        """
        Selects point in a given xarray with the supplied x, y local coordinates. 
        If a certain level of hight is passed as well, the time will be filtered as well.
        """
        if level:
            return xarrayData.sel(x=x, y=y, level=level)
        
        return xarrayData.sel(x=x, y=y)

def findPoint(xarray:xarray.core.dataset.Dataset, Point:dict):
    """
    Findes the closest lon, lat coordiante to a given Point in a xarray Dataset, where lon, lat is given as a value in dependency to the coordinates x, y.

    """
    abslat = np.abs(xarray.lat-Point["coor"][0])
    abslon = np.abs(xarray.lon-Point["coor"][1])
    c = np.maximum(abslon, abslat)
    
    if 'level' in xarray.dims and 'level' in Point.keys():
        abslev = np.abs(xarray.level-Point["level"])
        nearestlevel = np.where(abslev == np.min(abslev))
        nearestlevel = xarray.level[nearestlevel]
        return np.where(c == np.min(c)), nearestlevel
    
    return np.where(c == np.min(c)), None

def getPointData(xarray:xarray.core.dataset.Dataset, x, y, level=None, time=None):
    """
    Selects point in a given xarray with the supplied x, y local coordinates. 
    If a certain level of hight is passed as well, the time will be filtered as well.
    """
    if level:
        return xarray.sel(x=x, y=y, level=level)
    
    return xarray.sel(x=x, y=y)


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