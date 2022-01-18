
import pandas
import sqlalchemy
from enum import Enum, unique

@unique
class DatabaseType(Enum):
    POSTGRESQL="postgres"
    MYSQL="mysql"
    MESAP="mesap"
    ORACLE="oracle"


def _build_postgres_conn_string (param:dict) -> str:
    """[summary]

    Args:
        param (dict): [description]

    Returns:
        str: [description]
    """
    return f'postgresql+psycopg2://{param["user"]}:{param["password"]}@{param["host"]}:{param["port"]}/{param["dbname"]}'

def _create_postgres_engine (param:dict) -> sqlalchemy.engine.base.Engine:
    """[summary]

    Args:
        param (dict): [description]

    Returns:
        sqlalchemy.engine.base.Engine: [description]
    """
    con_string = _build_postgres_conn_string(param)
    engine = sqlalchemy.create_engine(con_string, pool_recycle=3600)
    return engine

def read_postgres_from_queryfile (
        sql_query_path:str, 
        db_conn_data:dict, 
        db_type:DatabaseType=DatabaseType.POSTGRESQL
        ) -> pandas.DataFrame:
    """[summary]

    Args:
        sql_query_path (str): [description]
        db_conn_data (dict): [description]
        db_type (DatabaseType, optional): [description]. Defaults to DatabaseType.POSTGRESQL.

    Returns:
        pandas.DataFrame: [description]
    """

    if db_type.value == "postgres":
        engine =  _create_postgres_engine(db_conn_data)
        
        scriptFile = open(sql_query_path,'r')
        script = scriptFile.read()
        df = pandas.read_sql(script, engine)

    if db_type.value == "mysql":
        pass

    if db_type.value == "mesap":
        pass

    if db_type.value == "oracle":
        pass

    return df