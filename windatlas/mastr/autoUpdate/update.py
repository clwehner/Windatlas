import logging
from multiprocessing import connection
import os
from enum import Enum, unique

from bs4 import BeautifulSoup
import urllib3

import requests, zipfile
import pandas
import sqlalchemy

##### Defining Constants

from global_setup import _CONN_PARAMS_DIC

_MASTR_URL = "https://www.marktstammdatenregister.de/MaStR/Datendownload"
_XML_DUMMY_PATH = r"/uba/mastr/MaStR/Vollauszüge/recent/"
_XML_FILTER = ["Netzanschlusspunkte"] # More can be added...

##### Defining logging function

dir_path = os.path.dirname(os.path.realpath(__file__))
file_name = os.path.join(dir_path, 'update_log.log')

#print(file_name)

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(file_name)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

#os.chmod(file_name, 775)

def do_logging(info_str):
    logger.info(info_str)

##### Define Enums for MaStR-DB update functionality
@unique
class DataType(Enum):
    """
    DataType
    This Enums are used to deliver valid data types while handeling data downloaded from the mastr.
    """

    XML = ".xml"

##### Defining classes to download and update mastr DB

class MastrDownloader():
    def __init__(self):
        self.url=_MASTR_URL
        self.downloadDir=_XML_DUMMY_PATH

    def clear_directory(self, dataType:DataType=DataType.XML):
        """[summary]

        Args:
            dataType (str, optional): [description]. Defaults to ".xml".
        """
        filelist = [ f for f in os.listdir(self.downloadDir) if f.endswith(dataType.value) ]
        do_logging(f"Found {len(filelist)} files to delete.")
        for f in filelist:
            os.remove(os.path.join(self.downloadDir, f))

    def get_mastr_download_link(self):
        """[summary]
        """
        http = urllib3.PoolManager()

        response = http.request('GET', self.url)
        soup = BeautifulSoup(response.data, features="lxml")

        for link in soup.findAll('a'):
            if str(link.get('href')).endswith(".zip"):
                downloadString = str(link.get('href'))
                do_logging(f"Found file to download: {downloadString.split('/')[-1]}")

        self.downloadURL = downloadString

    def download_mastr_files(self):
        """[summary]
        """
        if not os.path.exists(self.downloadDir):
            os.makedirs(self.downloadDir)  # create folder if it does not exist

        file_name = self.downloadURL.split('/')[-1].replace(" ", "_")  # be careful with file names
        file_path = os.path.join(self.downloadDir, file_name)

        r = requests.get(self.downloadURL, stream=True)
        if r.ok:
            do_logging(f"saving to: {os.path.abspath(file_path)}")
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 8):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        os.fsync(f.fileno())
        else:
            do_logging("Download failed: status code {}\n{}".format(r.status_code, r.text))

        self.zipFilePath = os.path.abspath(file_path)

    def extract_mastr_files(self, deleteZipFiles:bool=True):
        """[summary]

        Args:
            deleteZipFiles (bool, optional): [description]. Defaults to True.
        """
        extension = ".zip"

        os.chdir(self.downloadDir)

        for item in os.listdir(self.downloadDir): # loop through items in dir
            if item.endswith(extension): # check for ".zip" extension
                file_name = os.path.abspath(item) # get full path of files
                zip_ref = zipfile.ZipFile(file_name) # create zipfile object
                zip_ref.extractall(self.downloadDir) # extract file to dir
                zip_ref.close() # close file
                if deleteZipFiles:
                    os.remove(file_name) # delete zipped file

class MastrDBUpdate():
    def __init__(self, xmlPath:str=_XML_DUMMY_PATH, dbParameterDic:dict=_CONN_PARAMS_DIC, xmlFilter:list=_XML_FILTER):
        self.xmlPath = xmlPath
        self.xmlFilter = xmlFilter
        self.xmlList = list()
        self.__db_parameter_dic = dbParameterDic
        self.__postgres_conn_string = self.__build_postgres_conn_string(param=self.__db_parameter_dic)

    def __build_postgres_conn_string (self, param:dict) -> str:
        return f'postgresql+psycopg2://{param["user"]}:{param["password"]}@{param["host"]}:{param["port"]}/{param["dbname"]}'

    def __create_postgres_engine (self):
        return sqlalchemy.create_engine(self.__postgres_conn_string, pool_recycle=3600) # , poolclass=NullPool)

    def xml_file_check(self, filter:bool=True, downloadMissing:bool=True):
        files = os.listdir(self.xmlPath)
        if not files or files[0].split(".")[-1].lower() != "xml":
            do_logging(f"No files or .xml files in directory: {self.xmlPath}")
            if downloadMissing:
                do_logging("Downloading and extracting todays 'Vollauszug' from MaStR Homepage into the mentioned directory.")
                mastrDownloader = MastrDownloader()
                mastrDownloader.clear_directory()
                mastrDownloader.get_mastr_download_link()
                mastrDownloader.download_mastr_files()
                mastrDownloader.extract_mastr_files()
            else:
                return

            files = os.listdir(self.xmlPath)

        files.sort()
        filenames = [element.split(".")[0].split("_")[0] for element in files]
        uniqueFilenames = list(set(filenames))

        stackedList = []
        for uniqueName in uniqueFilenames:
            filteredList = [self.xmlPath + k for k in files if uniqueName in k]
            stackedList.append(filteredList)

        if filter:
            for i, liste in enumerate(stackedList):
                stackedList[i] = [x for x in liste if all(y not in x for y in self.xmlFilter)]
            stackedList = [x for x in stackedList if x != []]
            do_logging(".xml choice for upload to DB filtered for listed invalid .xml's")
        
        self.xmlList = stackedList

    def xml_to_DataFrame(self, XMLpathList:list) -> pandas.DataFrame:
        listDfs = [pandas.read_xml(path_or_buffer=file, encoding="utf-16") for file in XMLpathList]
        return pandas.concat(listDfs,ignore_index=True)

    def __change_dtype_datetime(self, df:pandas.DataFrame) -> pandas.DataFrame:
        listOfDateCols = list(df.filter(regex="datum(?i)").columns) # search for datum case insensitive
    
        for col in listOfDateCols:
            df[col] = pandas.to_datetime(df[col], errors = 'ignore')

        return df

    def update_mastr_postgres(self):
        engine = self.__create_postgres_engine()

        if len(self.xmlList)==0:
            do_logging("")
            return

        for files in self.xmlList:
            tableName = files[0].split("/")[-1].split(".")[0].split("_")[0]

            do_logging(f"{tableName} start reading into dataFrame")
            listDfs = [pandas.read_xml(path_or_buffer=file, encoding="utf-16") for file in files]

            do_logging(f"{tableName} start concating dataFrames")
            df = pandas.concat(listDfs,ignore_index=True)

            do_logging("changing dtypes to dateTime")
            df = self.__change_dtype_datetime(df)

            do_logging(f"{tableName} load dataFrames into Postgres-DB")
            df.to_sql(
                name=tableName,
                schema="mastr_raw",
                con=engine,
                if_exists="replace",
                index=False
            )

            if "Breitengrad" and "Laengengrad" in  df.columns:
                self.postGis_add_coordinates (engine=engine, tableName=tableName)

            del(df, listDfs, tableName)
            do_logging(".")

        engine.dispose()
        do_logging("connection to DB disposed")


    def postGis_add_coordinates (
            self,
            engine,
            tableName:str,
        ):
        query = f'ALTER TABLE mastr_raw."{tableName}" ADD COLUMN geom geometry(Point, 4326); UPDATE mastr_raw."{tableName}" SET geom = ST_SetSRID(ST_MakePoint("{tableName}"."Laengengrad", "{tableName}"."Breitengrad"), 4326);'
        
        connection = engine.connect()
        results = connection.execute(query)#.fetchall()

        do_logging(f"postGIS points added to: {tableName}")


##### Defining main function to run

if __name__ == '__main__':
    do_logging("#######   DATABASE UPDATE STARTED   #######")

    # downloading and extracting recent mastr files
    mastrDownloader = MastrDownloader()
    mastrDownloader.clear_directory()
    mastrDownloader.get_mastr_download_link()
    mastrDownloader.download_mastr_files()
    mastrDownloader.extract_mastr_files()

    # pushing new mastr date to postgresql
    mastrDBUpdater = MastrDBUpdate()
    mastrDBUpdater.xml_file_check()
    mastrDBUpdater.update_mastr_postgres()

    do_logging("#######   DATABASE UPDATE SUCCESSFUL   #######")
