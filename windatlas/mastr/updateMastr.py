import pandas 
import numpy
import os
import datetime


TODAY = datetime.date.today()
PATH_VOLLAUSZUEGE = "/uba/mastr/MaStR/Vollauszüge/"
# LINK_TO_MASTR_DOWNLOAD = "https://download.marktstammdatenregister.de/Gesamtdatenexport_20211026__0f6c15ab579b42c09f49be45db2de174.zip"


def check_dir_from_today(path:str=PATH_VOLLAUSZUEGE, date:datetime.date=TODAY):
    """
    Check if a directory for the current day exists and returns path.
    """
    strDate = date.strftime("%Y%m%d")

    dateDirs = os.listdir(path)
    dates = numpy.array(dateDirs).astype("int")
    recentDir = str(dates.max())

    if not recentDir == strDate:
        create_dir_for_today(strDate)
    return path + strDate + "/"

def create_dir_for_today(date:str, path:str=PATH_VOLLAUSZUEGE) -> str:
    """
    Creats directory with name of today.
    """
    newDir = path + date + "/"
    bashCall = "sudo mkdir " + newDir
    os.system(bashCall)

def list_xml_files(path:str=PATH_VOLLAUSZUEGE) -> list:
    """
    
    """
    dirToday = check_dir_from_today()
    files = os.listdir(dirToday)
    files.sort()
    filenames = [element.split(".")[0].split("_")[0] for element in files]
    uniqueFilenames = list(set(filenames))

    stackedList = []
    for uniqueName in uniqueFilenames:
        filteredList = [path + k for k in files if uniqueName in k]
        stackedList.append(filteredList)
    
    return stackedList

def from_xml_to_DataFrame(XMLpathList:list) -> pandas.core.frame.DataFrame:
    """
    
    """
    listDfs = [pandas.read_xml(path_or_buffer=file, encoding="utf-16") for file in XMLpathList]
    return pandas.concat(listDfs,ignore_index=True)

if __name__ == "__main__":
    files = list_xml_files()
    print(files)