import requests, zipfile, io

def unzipFile(fileLink:str, extractionPath:str):
    r = requests.get(fileLink)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(extractionPath)