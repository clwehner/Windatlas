import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

import xarray as xr
import numba as nb
import timeit

import matplotlib.pyplot as plt

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from plotly.tools import mpl_to_plotly

from windFunctions import *

### Import MaStR-Data

weaData = pd.read_excel(r'./MaStR/20210426_Wind.xlsx')
weaData = weaData.dropna(subset=['Koordinate: Breitengrad (WGS84)', 'Koordinate: Längengrad (WGS84)'])
weaData["Inbetriebnahmedatum der Einheit"] = pd.to_datetime(weaData["Inbetriebnahmedatum der Einheit"], format='%d.%m.%Y')
weaData['Koordinate: Längengrad (WGS84)'] = weaData['Koordinate: Längengrad (WGS84)'].str.replace(",",".")
weaData['Koordinate: Breitengrad (WGS84)'] = weaData['Koordinate: Breitengrad (WGS84)'].str.replace(",",".")

weaData = weaData.astype({
    'Koordinate: Längengrad (WGS84)':'float',
    'Koordinate: Breitengrad (WGS84)':'float',
    'Rotordurchmesser der Windenergieanlage':'float',
    'Nettonennleistung der Einheit':'float'})

hersteller = ['Enercon','Vestas','Nordex','GE','Siemens','Gamesa']

# Leerzeichen löschen
weaData['Typenbezeichnung'] = weaData['Typenbezeichnung'].str.replace(" ","")
# Bindestriche löschen
weaData['Typenbezeichnung'] = weaData['Typenbezeichnung'].str.replace("-","")
# Bindestriche löschen
weaData['Typenbezeichnung'] = weaData['Typenbezeichnung'].str.replace(",",".")
# Alle Buchstaben groß schreiben
weaData['Typenbezeichnung'] = weaData['Typenbezeichnung'].str.upper()
weaData['Hersteller der Windenergieanlage'] = weaData['Hersteller der Windenergieanlage'].str.upper()
# Herstellernamen aus der Typbezeichnung löschen 
for Hersteller in hersteller:
    weaData['Typenbezeichnung'] = weaData['Typenbezeichnung'].str.replace(Hersteller.upper(),"")

### load wind data

path = r"./netCDF/windData/wspd.7L.2017-T.ts.nc"

data2016 = xr.open_dataset(path)

point = {
    "level":131,
    "y":0,
    "x":0,
    "coor":[47.22,5.899],
    "nearestLevel":0,
    "time":pd.to_datetime(["2016-05-01"])
}

([yloc], [xloc]), nlevel  = findPoint(data2016, point)

point3D = getPointData(xarray=data2016, x=xloc, y=yloc, level=nlevel)
windData = point3D.wspd.to_dataframe()
windData.reset_index(inplace=True)

path = r"./netCDF/windData/D-3km.E5.dirStats.140m.2008-2017.nc"

data140m = xr.open_dataset(path)

point = {
    "level":114,
    "y":0,
    "x":0,
    "coor":[50,10],
    "time":pd.to_datetime(["2016-05-01"])
}

([yloc], [xloc]), nlevel  = findPoint(data140m, point)

point_stat = getPointData(xarray=data140m, x=xloc, y=yloc)

### build Wind dash

inputDates = np.sort(weaData["Inbetriebnahmedatum der Einheit"].dt.year.unique())
inputList = []
for date in inputDates[3:]:
    inputList.append({"label": str(date), "value": int(date)})

markers = {}
for date in inputDates[3:-1:5]:
    markers.update({int(date): str(date)})

rangeMin = inputList[0]['value']
rangeMax = inputList[-1]['value']

####### app layout

app = dash.Dash(__name__)

app.title = "Windatlas"

server = app.server

app.layout = html.Div([
    html.H1("MaStR Dashboard Demo", style={'text-align': 'center','color': 'white'}),

    dcc.RangeSlider(
        id = 'range-slider',
        min = rangeMin,
        max = rangeMax, 
        marks = markers,
        value = [rangeMin + 20,rangeMax],
        updatemode='drag'),

    html.Div(
        id='output_container', 
        children=[], 
        style={'color':'black'}),

    html.Br(),

    dcc.Graph(
        id="scatter-plot",
        figure={}),
    
    html.Div([
        html.Div([
            dcc.Graph(
                id = 'mastr_map', 
                figure={})],
            className="map__container",
        ),
        

        html.Div([
            html.Img(
                id = 'windrose1', 
                src = ''),
            
            html.Img(
                id = 'windrose2', 
                src = '')],
            className="Histogram__container",
            )
        ]
    )
])

####### app callbacks

### RANGESLIDER ###
@app.callback(
    Output('output_container', 'children'),
    Input('range-slider', 'value'))
def update_range(value):
    start = str(value[0])
    end = str(value[1])

    container = 'The year chosen by user was: {} - {}'.format(start, end)

    test = weaData[(weaData["Inbetriebnahmedatum der Einheit"] >= start) & (weaData["Inbetriebnahmedatum der Einheit"] < end) & (weaData["Nettonennleistung der Einheit"] < 8000)]

    return container


### SCATTERMAP ###
@app.callback(
    Output('mastr_map', 'figure'),
    Input('range-slider', 'value'))
def update_map(value):
    start = str(value[0])
    end = str(value[1])

    test = weaData[(weaData["Inbetriebnahmedatum der Einheit"] >= start) & (weaData["Inbetriebnahmedatum der Einheit"] < end)]

    mapScatter = px.scatter_mapbox(
        test, 
        lat='Koordinate: Breitengrad (WGS84)', 
        lon='Koordinate: Längengrad (WGS84)', 
        hover_name="MaStR-Nr. der Einheit", 
        hover_data=["Hersteller der Windenergieanlage",'Typenbezeichnung', "Nettonennleistung der Einheit", "Inbetriebnahmedatum der Einheit"],
        color = 'Nettonennleistung der Einheit',  
        color_discrete_sequence=px.colors.qualitative.G10, 
        zoom=3, 
        height=600,
        mapbox_style="open-street-map")
    mapScatter.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        mapbox=dict(
            pitch=60,
            bearing=30))

    return mapScatter

### SCATTERPLOT ###
@app.callback(
    Output('scatter-plot', 'figure'),
    Input('range-slider', 'value'))
def update_scat(value):
    start = str(value[0])
    end = str(value[1])

    # test = weaData[(weaData["Inbetriebnahmedatum der Einheit"] >= start) & (weaData["Inbetriebnahmedatum der Einheit"] < end)]

    # scatter = px.scatter(
    #     test, 
    #     x='Rotordurchmesser der Windenergieanlage', 
    #     y="Nettonennleistung der Einheit", 
    #     hover_name="MaStR-Nr. der Einheit", 
    #     hover_data=["Hersteller der Windenergieanlage",'Typenbezeichnung', "Nettonennleistung der Einheit", "Inbetriebnahmedatum der Einheit"])
    #     # color = 'Inbetriebnahmedatum der Einheit')
    #     # color_discrete_sequence=px.colors.qualitative.G10)

    fig = px.line(windData, x="time", y="wspd", title='Windgeschwindigkeiten')

    return fig

### WINDROSES ###
@app.callback(
    Output(component_id='windrose1', component_property='src'),
    Input('range-slider', 'value'))
def update_scat(value):
    start = str(value[0])
    end = str(value[1])

    fig = circularHisto(point_stat, dataVariable="histo")
    circularHisto(point_stat, dataVariable="wspd", grid=True)
    out_url = fig_to_uri(fig)
    return out_url

@app.callback(
    Output(component_id='windrose2', component_property='src'),
    Input('range-slider', 'value'))
def update_scat(value):
    start = str(value[0])
    end = str(value[1])

    fig = circularHisto(point_stat, dataVariable="wspd", grid=True)
    out_url = fig_to_uri(fig)
    return out_url

####### start app
if __name__ == "__main__":
    app.run_server(port=8052)
