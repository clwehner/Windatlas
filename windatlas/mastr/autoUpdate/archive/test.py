import logging
import os
from bs4 import BeautifulSoup
import urllib3
import sys 
import pandas as pd

dir_path = os.path.dirname(os.path.realpath(__file__))
filename = os.path.join(dir_path, 'test_log.log')

print(filename)

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(filename)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

#os.chmod(filename, 1775)

# Webcrowler
http = urllib3.PoolManager()

url = "https://www.marktstammdatenregister.de/MaStR/Datendownload"
response = http.request('GET', url)
soup = BeautifulSoup(response.data)

for link in soup.findAll('a'):
    if str(link.get('href')).endswith(".zip"):
        downloadString = str(link.get('href'))
        # print(downloadString)

def do_logging(str):
    logger.info(str)



if __name__ == '__main__':
    do_logging(downloadString)
    do_logging(f"Version Pandas: {pd.__version__}")
    do_logging(f"Version Python: {sys.version}")
