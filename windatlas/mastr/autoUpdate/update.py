import logging
import os

from bs4 import BeautifulSoup
import urllib3

import requests, zipfile, io
import pandas
import sqlalchemy

#####

URL = "https://www.marktstammdatenregister.de/MaStR/Datendownload"

XML_DUMMY_PATH = r"/uba/mastr/MaStR/Vollauszüge/recent/"
CONN_PARAMS_DIC = {
    "host": "10.0.0.102",
    "dbname": "mastr",
    "user": "uba_user",
    "password": "UBAit2021!",
    "port": "5432"
}

dir_path = os.path.dirname(os.path.realpath(__file__))
filename = os.path.join(dir_path, 'update_log.log')

print(filename)

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(filename)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

def do_logging(infoStr):
    logger.info(infoStr)

# webcrowler
def getMaStRDownloadlink() -> str:
    http = urllib3.PoolManager()

    response = http.request('GET', URL)
    soup = BeautifulSoup(response.data, features="lxml")

    for link in soup.findAll('a'):
        if str(link.get('href')).endswith(".zip"):
            downloadString = str(link.get('href'))
            # print(downloadString)

    return downloadString

# Downlaod and Unzipping
ZIP_UNIX_SYSTEM = 3

def extract_all_with_permission(zf, target_dir):
  for info in zf.infolist():
    extracted_path = zf.extract(info, target_dir)

    if info.create_system == ZIP_UNIX_SYSTEM:
      unix_attributes = info.external_attr >> 16
      if unix_attributes:
        os.chmod(extracted_path, unix_attributes)

def downloadMastrFiles(downloadDir:str):
    """
    
    """
    linkToZip = getMaStRDownloadlink()
    r = requests.get(linkToZip)
    # z = zipfile.ZipFile(io.BytesIO(r.content))
    # z.extractall(downloadDir)
    with zipfile.ZipFile(io.BytesIO(r.content), 'r') as zip_ref:
        zip_ref.extractall(downloadDir, pwd=b'qpsqpwsr')
        #extract_all_with_permission(zip_ref, downloadDir)

# Loading xml to Pandas
def list_xml_files(path:str=XML_DUMMY_PATH) -> list:
    """
    
    """
    files = os.listdir(path)
    if not files or files[0].split(".")[-1].lower() != "xml":
        do_logging(f"No files in directory: {path}")
        do_logging(f"No .xml files in directory: {path}")
        do_logging("Download and extract todays 'Vollauszug' from MaStR Homepage into the mentioned directory.")

        downloadMastrFiles(downloadDir=path)
        files = os.listdir(path)
        #return

    files.sort()
    filenames = [element.split(".")[0].split("_")[0] for element in files]
    uniqueFilenames = list(set(filenames))

    stackedList = []
    for uniqueName in uniqueFilenames:
        filteredList = [path + k for k in files if uniqueName in k]
        stackedList.append(filteredList)
    
    return stackedList


# Load to Pandas
def build_postgres_conn_string (param:dict) -> str:
    """

    """
    return f'postgresql+psycopg2://{param["user"]}:{param["password"]}@{param["host"]}:{param["port"]}/{param["dbname"]}'

def create_postgres_engine (param:dict=CONN_PARAMS_DIC):
    """
    
    """
    conString = build_postgres_conn_string(param)
    engine = sqlalchemy.create_engine(conString, pool_recycle=3600) # , poolclass=NullPool)
    return engine

def from_xml_to_DataFrame(XMLpathList:list) -> pandas.core.frame.DataFrame:
    """
    
    """
    listDfs = [pandas.read_xml(path_or_buffer=file, encoding="utf-16") for file in XMLpathList]
    return pandas.concat(listDfs,ignore_index=True)

def change_Dtype_Datetime(df:pandas.core.frame.DataFrame):# -> pandas.core.frame.DataFrame:
    """
    docstring
    """
    listOfDateCols = list(df.filter(regex="datum(?i)").columns) # search for datum case insensitive
    
    for col in listOfDateCols:
        df[col] = pandas.to_datetime(df[col], errors = 'ignore')



if __name__ == '__main__':
    downloadString = getMaStRDownloadlink()
    do_logging("Link found: " + downloadString)

    stackedList = list_xml_files()
    do_logging(".xml downloaded")

    filterList = ["Netzanschlusspunkte"] # More can be added...

    for i, liste in enumerate(stackedList):
        stackedList[i] = [x for x in liste if all(y not in x for y in filterList)]
    stackedList = [x for x in stackedList if x != []]
    do_logging(".xml choice for upload to DB filtered for invalid .xml's")


    engine = create_postgres_engine(CONN_PARAMS_DIC)

    for files in stackedList:
        tableName = files[0].split("/")[-1].split(".")[0].split("_")[0]

        do_logging(f"{tableName} start reading into dataFrame")
        ListDfs = [pandas.read_xml(path_or_buffer=file, encoding="utf-16") for file in files]

        do_logging(f"{tableName} start concating dataFrames")
        df = pandas.concat(ListDfs,ignore_index=True)

        do_logging("Changing dtypes to dateTime")
        change_Dtype_Datetime(df)

        do_logging(f"{tableName} load dataFrames into Postgres-DB")
        df.to_sql(
            name=tableName,
            schema="mastr_raw",
            con=engine,
            if_exists="replace",
            index=False
        )
        del(df, ListDfs, tableName)
        do_logging(".")

    engine.dispose()
    do_logging("Connection to DB disposed")
