import ipywidgets as ipw
from IPython.display import display

import datetime
import sqlalchemy
import pandas

import plotly.express as px

from datetime import date

import warnings
warnings.filterwarnings('ignore')

class SolarApp():
    __SQL_PATH = r"./sqlCommands/"
    __SQL_DATA = r"loadMastrSolar.sql"

    # Parameters to create a connection to the MaStR-postgreSQL DB
    __CONN_PARAM_DICT = {
        "host": "10.0.0.102",
        "dbname": "mastr",
        "user": "uba_user",
        "password": "UBAit2021!",
        "port": "5432"
    }

    __bundeslaender = {
        1400:"Brandenburg",
        1401:"Berlin",
        1402:"Baden-Würtenberg",
        1403:"Bayern",
        1404:"Bremen",
        1405:"Hessen",
        1406:"Hamburg",
        1407:"Mecklenburg-Vorpommern",
        1408:"Niedersachsen",
        1409:"Nordrhein-Westfahlen",
        1410:"Rheinland-Pfalz",
        1411:"Schleswig-Holstein",
        1412:"Saarland",
        1413:"Sachsen",
        1414:"Sachsen-Anhalt",
        1415:"Thüringen"}

    solarDf = None

    def __init__(self):
        self.__SQL_DATA_PATH = self.__SQL_PATH + self.__SQL_DATA
        self.buildApp()

    # DATABASE STUFF
    def build_postgres_conn_string (self, param:dict) -> str:
        return f'postgresql+psycopg2://{param["user"]}:{param["password"]}@{param["host"]}:{param["port"]}/{param["dbname"]}'

    def create_postgres_engine (self, param:dict) -> sqlalchemy.engine.base.Engine:
        conString = self.build_postgres_conn_string(param)
        engine = sqlalchemy.create_engine(conString, pool_recycle=3600)
        return engine

    def read_postgres_from_queryfile (self) -> pandas.DataFrame:
        engine = self.create_postgres_engine(self.__CONN_PARAM_DICT)
        
        scriptFile = open(self.__SQL_DATA_PATH,'r')
        script = scriptFile.read()
        df = pandas.read_sql(script, engine)
        df = df.replace({"Bundesland": self.__bundeslaender})
        df["Anlagenzahl"] = 1

        return df

    # ANALYSE FUNKTIONEN

    def classify_Leistung(self,NennLeistung,threshklasse):
        Klasse = None

        for n, k in enumerate(threshklasse):
            if k == threshklasse [-1]:
                if NennLeistung > threshklasse[n]:
                    Klasse = k
            else:
                if NennLeistung > threshklasse[n] and NennLeistung <= threshklasse [n+1]: 
                    Klasse = k

        return Klasse

    # BUTTON FUNCTIONS
    def on_button_load_mastr (self,*args):
        with self.out_button_load_mastr:
            self.out_button_load_mastr.clear_output()
            print("Lade MaStR-Daten...")
            self.solarDf = self.read_postgres_from_queryfile()
            self.out_button_load_mastr.clear_output()
            print("MaStR-Daten Geladen!")
            #display(self.solarDf.iloc[0:5,0:4])

    def on_button_classify_solar(self,*args):
        with self.out_button_classify_solar_group:
            self.out_button_classify_solar_group.clear_output()
            if self.solarDf is None:
                print("Daten müssen zuerst aus der MaStR-Datenbank geladen werden.\nKlicke dafür auf das Feld 'Lade MaStR Daten aus Datenbank' oben links.")
                return
            
            # Filtern nach Inbetriebnahmedatum
            start = pandas.to_datetime(self.dateSlider.value[0])
            end = pandas.to_datetime(self.dateSlider.value[1])
            print("Zeitfenster:")
            print(f"{start} bis {end}")

            # Gruppierung nach Größenklassen
            klassenList = [int(i) for i in self.groessenklassen.value.split(",")]
            klassenList.sort()
            print("Klassen:")
            print(klassenList)

            cutdf = self.solarDf.loc[(self.solarDf.loc[:,'Inbetriebnahmedatum'] >= start) & (self.solarDf.loc[:,'Inbetriebnahmedatum'] <= end),:]
            cutdf.loc[:,"Groessenklasse"] = cutdf.apply(lambda x: self.classify_Leistung(NennLeistung=x["Nettonennleistung"],threshklasse= klassenList), axis=1)
            cutdf["Groessenklasse"] = cutdf["Groessenklasse"].astype(str)
            self.classifiedDf = cutdf
            #self.out_button_classify_solar_group.clear_output()
            #print("fertig klassifiziert")
            self.groupedDf = cutdf.groupby(["Groessenklasse"]).sum().reset_index()

            df = self.groupedDf

            for i in df.index:
                if i < df.index.max():
                    print(str(df.loc[i, "Groessenklasse"]) + " - " + str(float(df.loc[i+1, "Groessenklasse"]) - 0.1))
                    df.loc[i, "Groessenklasse"] = str(df.loc[i, "Groessenklasse"]) + " - " + str(float(df.loc[i+1, "Groessenklasse"]) - 0.1)
                else:
                    print(str(df.loc[i, "Groessenklasse"]) + " +")
                    df.loc[i, "Groessenklasse"] = str(df.loc[i, "Groessenklasse"]) + " +"

            self.groupedDf = df

            display(self.groupedDf.loc[:,["Groessenklasse","Nettonennleistung","Anlagenzahl"]])
    
    # APP LAYOUT
    def buildApp (self):
        title = ipw.HTML('<span style="color:#FF0000"> Klassifizierung von Solaranlagen </span>')
        hbox_title = ipw.HBox([title])
        hbox_title.layout.justify_content = "center"

        self.button_load_mastr = ipw.Button(
            description='Lade MaStR Daten aus Datenbank',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Lade MaStR Daten aus Datenbank',
            display='flex',
            style=dict(description_width='initial'),
        )
        self.out_button_load_mastr = ipw.Output()
    
        self.button_load_mastr.on_click(self.on_button_load_mastr)
        mastrButton = ipw.VBox([self.button_load_mastr, self.out_button_load_mastr])
        mastrButton.layout.justify_content = "center"

        layout = ipw.Layout(width='auto', height='40px')
        self.groessenklassen = ipw.Text(
            value="0,5,10,100,500",
            placeholder="5,10,100",
            description="Untere Größenklassengrenze:",
            disable = False,
            display='flex',
            layout = layout,
            style=dict(description_width='initial'),
        )
        anlagentyp = ipw.Dropdown(
            options = ["Dachanlagen", "Freiflächenanlagen", "Dach- und Freiflächenanlagen"],
            value = "Dach- und Freiflächenanlagen",
            description = "Anlagentyp:",
            disable = False,
            display='flex',
            layout = layout,
        )
        hbox_select = ipw.HBox([self.groessenklassen, anlagentyp])
        hbox_select.layout.justify_content = "center"

        dates = pandas.date_range(start="1990-01", end=date.today(), freq="MS").tolist()
        options = [(i.strftime("%Y/%m"), i) for i in dates]
        self.dateSlider = ipw.SelectionRangeSlider(
            options=options,
            index=(0, 100),
            description='Monate 1990 - Heute:',
            disabled=False,
            style=dict(description_width='initial'),
            layout = ipw.Layout(width='50%', height='40px', lign_items='center',),
        )
        hbox_dateslider = ipw.HBox([self.dateSlider])
        hbox_dateslider.layout.justify_content = "center"

        self.button_classify_solar = ipw.Button(
            description='Berechnen',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Berechnen',
        )
        self.out_button_classify_solar_group = ipw.Output()

        self.button_classify_solar.on_click(self.on_button_classify_solar)
        hbox_button = ipw.HBox([self.button_classify_solar])
        hbox_button.layout.justify_content = "center"
        hbox_out = ipw.HBox([self.out_button_classify_solar_group])
        hbox_out.layout.justify_content = "center"


        self.app = ipw.VBox([hbox_title, mastrButton, hbox_select, hbox_dateslider, hbox_button, hbox_out])

    def display(self):
        return self.app

    

