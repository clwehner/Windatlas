import psycopg2
import pandas 
import flask
import sys
import os


#%% Reading Data from xml to pandas

def from_xml_to_DataFrame(pathToXML:str) -> pandas.core.frame.DataFrame:
    """
    
    """
    return pandas.read_xml(path_or_buffer=pathToXML, encoding="utf-16")


def change_Dtype_Datetime(df:pandas.core.frame.DataFrame):# -> pandas.core.frame.DataFrame:
    """
    docstring
    """
    listOfDateCols = list(df.filter(regex="datum(?i)").columns) # search for datum case insensitive
    
    for col in listOfDateCols:
        df[col] = pandas.to_datetime(df[col], errors = 'ignore')


#%% Support Functions psycopg2 

def show_psycopg2_exception(err):
    """
    Function that handles and parses psycopg2 exceptions
    """
    # get details about the exception
    err_type, err_obj, traceback = sys.exc_info()    
    # get the line number when exception occured
    line_n = traceback.tb_lineno    
    # print the connect() error
    print ("\npsycopg2 ERROR:", err, "on line number:", line_n)
    print ("psycopg2 traceback:", traceback, "-- type:", err_type) 
    # psycopg2 extensions.Diagnostics object attribute
    print ("\nextensions.Diagnostics:", err.diag)    
    # print the pgcode and pgerror exceptions
    print ("pgerror:", err.pgerror)
    print ("pgcode:", err.pgcode, "\n")
    

def connect(conn_params:dict) -> psycopg2.extensions.connection:
    """
    Define a connect function for PostgreSQL database server. 
    The conn_params dict can include the following keys:

    conn_params_dic = {
        "host": "host_name",
        "dbname": "dbname",
        "user": "user",
        "password": "password",
        "port": "port"
    }
    """
    conn = None
    try:
        print('Connecting to the PostgreSQL...........')
        conn = psycopg2.connect(**conn_params)
        print("Connection successfully..................")
     
    except psycopg2.OperationalError as err:
        # passing exception to function
        show_psycopg2_exception(err)        
        # set the connection to 'None' in case of error
        conn = None
    return conn
    

def copy_from_DataFrame(conn:psycopg2.extensions.connection, df:pandas.core.frame.DataFrame, table:str):
    """
    Function using copy_from_dataFile to insert the dataframe.
    """
    # Here we are going save the dataframe on disk as a csv file, load # the csv file and use copy_from() to copy it to the table
    tmp_df = "./Learn Python Data Access/df_temp.csv"
    df.to_csv(tmp_df, header=False,index = False)
    f = open(tmp_df, 'r')
    cursor = conn.cursor()
    try:
        cursor.copy_from(f, table, sep=",")
        conn.commit()
        print("Data inserted using copy_from_datafile() successfully....")
        cursor.close()
    except (Exception, psycopg2.DatabaseError) as err:
        os.remove(tmp_df)
        # pass exception to function
        show_psycopg2_exception(err)
        cursor.close()
    os.remove(tmp_df)