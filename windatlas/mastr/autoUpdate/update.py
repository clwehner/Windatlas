import logging
import os

from webCrowler import getMaStRDownloadlink
from xmlToDb import unzipFile
#####
# VARIABLES
XML_DUMMY_PATH = r"/uba/mastr/MaStR/Vollauszüge/recent/"


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

def do_logging(infoStr):
    logger.info(infoStr)

if __name__ == '__main__':
    downloadString = getMaStRDownloadlink()
    do_logging("Link found: " + downloadString)
    unzipFile(fileLink= downloadString,
        extractionPath= XML_DUMMY_PATH)