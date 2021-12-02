import requests, zipfile, io
import pandas as pd
import numpy as np
import sqlalchemy
from postgressql import *

# Variables

XML_DUMMY_PATH = r"/uba/mastr/MaStR/Vollauszüge/recent/"
CONN_PARAMS_DIC = {
    "host": "10.0.0.102",
    "dbname": "mastr",
    "user": "uba_user",
    "password": "UBAit2021!",
    "port": "5432"
}

# Unzipping

def unzipFile(fileLink:str, extractionPath:str=XML_DUMMY_PATH):
    """
    
    """
    r = requests.get(fileLink)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(extractionPath)

# Loading xml to Pandas

def build_postgres_conn_string (param:dict) -> str:
    """

    """
    return f'postgresql+psycopg2://{param["user"]}:{param["password"]}@{param["host"]}:{param["port"]}/{param["dbname"]}'

def create_postgres_engine (param:dict):
    """
    
    """
    conString = build_postgres_conn_string(param)
    engine = sqlalchemy.create_engine(conString, pool_recycle=3600)
    return engine

def read_postgres_from_queryfile (sqlpath:str, postgresLogin:dict=CONN_PARAMS_DIC):# -> pandas.core.frame.DataFrame:
    """

    """
    engine = create_postgres_engine(postgresLogin)
    
    scriptFile = open(sqlpath,'r')
    script = scriptFile.read()
    df = pd.read_sql(script, engine)

    return df