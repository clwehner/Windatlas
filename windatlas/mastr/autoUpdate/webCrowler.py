from bs4 import BeautifulSoup
import urllib3

URL = "https://www.marktstammdatenregister.de/MaStR/Datendownload"

def getMaStRDownloadlink() -> str:
    http = urllib3.PoolManager()

    response = http.request('GET', URL)
    soup = BeautifulSoup(response.data)

    for link in soup.findAll('a'):
        if str(link.get('href')).endswith(".zip"):
            downloadString = str(link.get('href'))
            # print(downloadString)

    return downloadString