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
        print(f"Most recent directory is: {recentDir}")
        print(f"Creat a directory for today: {strDate} ? [y/n]")
        answer = input()
        if answer == s"n":
            return None
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
    if not dirToday:
        print("No directory for today. Do you want to read from latest dir? [y/n]")
        answer = input()
        if answer == "n":
            return
        lastDir = os.listdir(path)
        lastDir = str(numpy.array(lastDir).astype("int").min())
        dirToday = path + lastDir + "/"
    
    files = os.listdir(dirToday)
    if not files:
        print(f"No files in directory: {dirToday}")
        print("Download and extract todays 'Vollauszug' from MaStR Homepage into the mentioned directory.")
        return
    
    if files[0].split(".")[-1].lower() != "xml":
        print(f"No .xml files in directory: {dirToday}")
        #TO DO: AUTOMATED DOWNLOAD FUNCTION
        return

    files.sort()
    filenames = [element.split(".")[0].split("_")[0] for element in files]
    uniqueFilenames = list(set(filenames))

    stackedList = []
    for uniqueName in uniqueFilenames:
        filteredList = [dirToday + k for k in files if uniqueName in k]
        stackedList.append(filteredList)
    
    return stackedList

def from_xml_to_DataFrame(XMLpathList:list) -> pandas.core.frame.DataFrame:
    """
    
    """
    listDfs = [pandas.read_xml(path_or_buffer=file, encoding="utf-16") for file in XMLpathList]
    return pandas.concat(listDfs,ignore_index=True)

if __name__ == "__main__":
    files = list_xml_files()
    print(f"List of .xml files: {files}")