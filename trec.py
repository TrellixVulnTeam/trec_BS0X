import requests
from bs4 import BeautifulSoup
import shutil
import os
import tarfile
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import gzip
import subprocess
import logging
import sys

# define nist website url, username and password  that you have receied here
url = 'https://ir.nist.gov/tweets2011'
user, password = 'tweets2011', 'NHwv6H4o'

# path config, you can rename those if you wish
currentFolder = os.path.dirname(os.path.realpath('__file__'))   
tarFolder = 'tarFiles'
untarFolder = 'openedTarFiles'
jsonFolder = 'jsonFiles'
logFolder = 'logFiles'
repairJsonFolder = 'repairJsonFiles'
tweetsFolder = 'tweets'
max = 17

# We wont use SSL since we trust the downloading page, so hide warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# get tweets from the dat files which are opened from the tar files
def getTweets(untarFolder, begin, end):

    list = os.listdir(untarFolder)

    # skip files that may be automatically added to folder like ".DS_STORE" in OS X
    for file in list:
        if "." in file:
            list.remove(file)

    list.sort()
    if reverse == True:
        list.reverse()

    if end > max:
        end = max
        print("Setting end point to maximum")
    

    print(end-begin+1)
    for i in range(0, end-begin):

        # dat file directory is in the same level with this script file, get its path
        datFolderPath = os.path.join(untarFolder, list[i])
    
        datFileList = os.listdir(datFolderPath)
        datFileList.sort()
        print(datFileList)
        for datFile in datFileList:
            # remove dat extension
            datFileName = os.path.splitext(datFile)[0]

            # Crate a path for downloaded tweets data and its repair data
            jsonPath = makePath(jsonFolder, datFileName + ".json.gz")
            repairJsonPath = makePath(repairJsonFolder, datFileName + ".json.gz")
            datFilePath = makePath(datFolderPath, datFile)
            fetcherPath = os.path.join("..", "target", "appassembler", "bin", "AsyncHTMLStatusBlockCrawler")
      
            with subprocess.Popen(['sh', fetcherPath, '\\'
   ,'-data',datFilePath,'-output', jsonPath, '\\', '-repair', repairJsonPath], stdout=subprocess.PIPE) as proc:
                path = makePath(logFolder,datFileName+".log")
                print("logging to:" + path)
                logging.basicConfig(filename=path, level=logging.DEBUG)
                logging.info(proc.stdout.read().decode('utf-8'))
    return

# Repair failed tweets
def repairTweets(repairJsonFolder):
    for repairFile in os.listdir(repairJsonFolder):
        repairFilePath = os.path.join(repairJsonFolder, repairFile)
        repairFile = os.path.splitext(repairFile)[0]
        fetcherPath = os.path.join("..", "target", "appassembler", "bin", "AsyncHTMLStatusBlockCrawler")

        if os.path.isdir(repairFilePath) == True:
            repairTweets(repairFilePath)
        else:
            repairFileName = makePath(jsonFolder, repairFile + ".repair.json.gz")
            with subprocess.Popen(['sh', fetcherPath ,'\\'
   ,'-data', repairFilePath, '-output', repairFileName], stdout=subprocess.PIPE) as proc:
                path = makePath(logFolder, repairFile+".repair.log")
                print("logging repair to:" + path)
                logging.basicConfig(filename=path, level=logging.DEBUG)
                logging.info(proc.stdout.read().decode('utf-8'))
    return

# Open gz file by creating new folder in  current directory
def openGzFiles(files):
    datFolders = []
    for file in files:
        tarFolder = os.path.abspath(os.path.join(file, "..","..", untarFolder))

        if ".tar" in file:
            with tarfile.open(file) as tar:
                def is_within_directory(directory, target):
                    
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    
                    return prefix == abs_directory
                
                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")
                
                    tar.extractall(path, members, numeric_owner=numeric_owner) 
                    
                
                safe_extract(tar, path=tarFolder)
                print("opening .tar.gz " + file)
                datFolders.append(tarFolder)
        else:
            baseName = os.path.basename(file)
            path = makePath(tarFolder, baseName)
            fileName = os.path.splitext(path)[0] 
            with gzip.open(file, 'rb') as file_in, open(fileName, 'wb') as file_out:
                file_content =file_in.read()
                file_out.write(file_content)
                print("opening .gz " + path)
                datFolders.append(path)
    return

def openTweets():
    os.makedirs(os.path.join(currentFolder,tweetsFolder), exist_ok=True)
    dirName = os.path.join(currentFolder, jsonFolder)
    for file in os.listdir(dirName):
        path = makePath(tweetsFolder, file)
        file = os.path.join(currentFolder, jsonFolder, file)
        fileName = os.path.splitext(path)[0]
        with gzip.open(file, 'rb') as file_in, open(fileName, 'wb') as file_out:
            file_content = file_in.read()
            file_out.write(file_content)
            print("opening json.gz" + path)                

# Download retrieved files from the webpage
def getFiles(files, begin, end):
    pathlist = []
    if reverse == True:
        files.reverse()

    if end > max:
        end = max
        print("Setting end point to maximum")

    for i in range (begin, end):
        print(str(i) + " " + str(begin) + " " + str(end))
        os.makedirs(os.path.join(currentFolder,tarFolder), exist_ok=True)
        downloadedFiles = os.listdir(tarFolder)
        # if files are already downloaded skip those
        if files[i] in downloadedFiles:
            path = makePath(tarFolder, str(files[i]))
            print(str(files[i]) + " is found in the path and will not be downloaded")
            pathlist.append(path)
            continue

        downloadURL = os.path.join(url, str(files[i]))
        resp = requests.get(downloadURL, auth=(user, password), verify=False, stream=True)
        if (resp.status_code == 200):
            print(downloadURL + ' is being downloaded.')
            path = makePath(tarFolder, str(files[i]))
            with open(path, 'wb') as file:
                resp.raw.decode_content = True
                shutil.copyfileobj(resp.raw, file)
            pathlist.append(path)
        else:
            print("Error while downloading " + downloadURL + " code : " + str(resp.status_code))
    return pathlist

# Create new folder inside the scripts path and create new files in this new path

def makePath(folderName, fileName): 
    # use os module to join those beacuse of different operating sytems have different file seperators
    file_path = os.path.join(currentFolder,folderName, fileName)

    # Create new dir if not exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    return file_path



# Download the tar file URLs from the parsed content
def getFileLinks(resp):
    fileList = []
    html = BeautifulSoup(resp.content, 'html.parser')
    print('Links are being added to download list.')
    for link in html.find_all('a'):
        if 'tar' in link.get('href'):
            fileList.append(link.get('href'))
    return fileList

# Connect to the webpage and authenticate
def connect(url, usr, pwd):
    resp = requests.get(url, auth=(user, password), verify=False)
    if(resp.status_code == 200): 
        print('Connection successful:' + str(resp.status_code))
        return resp
    else:
        print ('There is an error while connecting the site : ' + str(resp.status_code))


# cmd config
reverse = False
numberOfFolders = None

temp = 0
begin = 0
end = sys.maxsize

for arg in sys.argv:
    if arg != os.path.basename(__file__):
        if arg == "--reverse":
            reverse = True
        else:
            try:
                number = int(arg)
            except ValueError:
                print("Your input must be an integer for begin and end range")
            else:
                # sort the numbers in increasing order, if user input is 5 2, set begin to 2 and end to 5
                if(number >= 0):
                    if(number > temp):
                        begin = temp
                        end = number
                        temp = end
                    else:
                        begin = number
                        end = temp
                        temp = end
                else:
                    print("Please enter a positive integer")

# let the fun begin

resp = connect(url, user, password)
tar = getFileLinks(resp)
downloadedTar = getFiles(tar, begin, end)
openGzFiles(downloadedTar)
getTweets(untarFolder, begin, end)
repairTweets(repairJsonFolder)
#openTweets()
#openRepairTweets()
