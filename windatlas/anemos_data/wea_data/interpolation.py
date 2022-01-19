# -*- coding: utf-8 -*-
"""
Created on Mon Apr 19 12:05:26 2021

@author: WehnerC
"""
import numpy as np
import pandas as pd
from scipy import interpolate

import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D


def interpolate1DWindturbineData(
    windTurbine_df: pd.Series,
    incrementWindspeed: float,
    interpolationMethod: str = 'cubic',
    plot: bool = True,
    powerLimiter: bool = True):
    """
    TO DO: 
    - return an interpolated pd.Dataframe of the same build
    """
    # Defining x and y arrays of the initial data set
    x = np.array(windTurbine_df.index)
    y = np.array(windTurbine_df.values)
    z = float(windTurbine_df.name)
    oldIncrement = round(x[1] - x[0],6)


    # x array that will be used for interpolating new point values
    steps = int(((x[-1] - x[0])/incrementWindspeed) + 1)

    x_new = np.linspace(x[0], x[-1], steps)
    increment = round(x_new[1] - x_new[0], 6)

    if interpolationMethod in ['linear', 'nearest', 'zero', 'slinear', 'quadratic', 'cubic', 'previous', 'next']:
        # Interpolation step
        f = interpolate.interp1d(x, y, kind = interpolationMethod)
        # y array that contains the interpolated data points
        y_interp = f(x_new)

    if powerLimiter:
        maxOriginalPower = y.max()
        y_interp[y_interp > maxOriginalPower] = maxOriginalPower

    if plot:
        fig = plt.figure(figsize=(10,6))
        ax = fig.subplots()
        ax.plot(x_new, y_interp, alpha = 0.5, label = interpolationMethod)
        ax.scatter(x,y)
        plt.xlabel(f"windspeed (m/s)\n increment increase: {oldIncrement} -> {increment}m/s")
        plt.ylabel("wind turbine power output (kW)")
        plt.legend()
        plt.show()

    return pd.Series(data=y_interp, name=z, index=x_new)

def calcSteps(
    top: float,
    bottom: float,
    increment: float,
    corrector: int = 1):
    """This function calculates the number of steps between a passed top and bottom value, based on a passed increment.

    Args:
        top(float): highest value of the intervall
        bottom(float): lowest value of the intervall
        incement(flaot): desired increment of intervall
        corrector(int): corrector value counting difference due to python starting with 0 instead of 1
    Return:
        Number of steps in the desired intervall
    """
    return complex((top-bottom)/increment + corrector)

def interpolate2DWindturbineData(
    windTurbine_df: pd.DataFrame,
    incrementWindspeed: float,
    incrementAirDensity: float,
    interpolationMethod: str = 'cubic',
    plot: bool = True,
    powerLimiter: bool = True,
    figsize: tuple = (20,10)):
    """
    TO DO: 
    - change np.mgrid -> np.linespace in combination with np.meshgrid
    """
    # Building goal grid data based on min and max of passed windTurbine_df and increments for AirDensity and Windspeed
    x_orig = np.array(windTurbine_df.index)
    y_orig = np.array(windTurbine_df.columns, dtype='float')#.astype('float64')

    windMin = x_orig.min()
    windMax = x_orig.max()
    windSteps = calcSteps(top=windMax, bottom=windMin, increment=incrementWindspeed, corrector=1)

    densityMin = y_orig.min()
    densityMax = y_orig.max()
    densitySteps = calcSteps(top=densityMax, bottom=densityMin, increment=incrementAirDensity, corrector=2)

    grid_x, grid_y = np.mgrid[windMin:windMax:windSteps, densityMin:densityMax:densitySteps]


    # Prepare original windTurbine_df data for interpolation
    values = windTurbine_df.stack().values
    points = windTurbine_df.stack().index.values
    points = np.array([list(i) for i in points], dtype='float')


    # Interpolation based on passed interpolationMethod
    if interpolationMethod in ['nearest', 'linear', 'cubic']:
        grid_z = interpolate.griddata(points, values, (grid_x, grid_y), method=interpolationMethod)
    else:
        print('No valid interpolationMethod passed. Must be either: nearest, linear or cubic')
        pass


    # Clean interpolated data of "numerical-errors" from the interpolation in constant maximal areas
    if powerLimiter:
        maxOriginalPower = values.max()
        grid_z[grid_z > maxOriginalPower] = maxOriginalPower


    # Plotting base 
    if plot:
        # Set up a figure twice as wide as it is tall
        fig = plt.figure(figsize=figsize)
        colormap = cm.coolwarm #viridis


        #===============
        #  First subplot
        #===============
        # Set up the axes for the first plot
        ax = fig.add_subplot(1, 2, 1, projection='3d')

        # Original data split coordinate wise
        X_orig, Y_orig = np.meshgrid(x_orig, y_orig)
        Z = windTurbine_df.values.transpose()
        
        # Plot original data
        ax.plot_wireframe(X_orig, Y_orig, Z, linewidth=0.7)#, rstride=10, cstride=10)
        ax.contour(X_orig, Y_orig, Z, zdir='z', offset=10, cmap=colormap, alpha=0.9)
        ax.set_title('initial\nwind turbine data')
        ax.set_xlabel('windspeed (m/s)')
        ax.set_ylabel('air density (kg/m³)')
        ax.set_zlabel('power output (kW)')


        #===============
        # Second subplot
        #===============
        # Set up the axes for the second plot
        ax = fig.add_subplot(1, 2, 2, projection='3d')

        # Plot interpolated data with original data as reference
        ax.plot_surface(grid_x, grid_y, grid_z, cmap=colormap, alpha=0.7, edgecolor='none')
        ax.scatter(points.transpose()[0], points.transpose()[1], values, marker='o', color='k', s=7)
        ax.contourf(grid_x, grid_y, grid_z, zdir='z', offset=-100, cmap=colormap, alpha=0.5)
        ax.set_title('interpolated\nwind turbine data')
        ax.set_xlabel(f'windspeed (m/s)\nincrement: {incrementWindspeed}')
        ax.set_ylabel(f'air density (kg/m³)\nincrement: {incrementAirDensity}')
        ax.set_zlabel('power output (kW)')
        
        plt.tight_layout()
        plt.show()

    return pd.DataFrame(data=grid_z, columns=grid_y[0], index=grid_x.transpose()[0])