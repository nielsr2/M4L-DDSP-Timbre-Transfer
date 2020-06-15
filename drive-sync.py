
# **********************************************************************
# import libraries
import pythonosc
import argparse
from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os.path
import time, sys

# **********************************************************************
# for conversion
import numpy as np
import soundfile as sf
import librosa

# FOR AUTHENTICATIION
gauth = None
drive = None
gdID = None
client = None

# Keeping track
latency = 0
counter = 0
def createGDFolder():
    # check if folder exists
    existingFolder = drive.ListFile({'q': "'root' in parents and trashed=false and title = 'M4L-Timbre-Transfer-Folder'"}).GetList()
    # print("fl", type(file_list))
    # if not, create it and store ID for future use
    if not existingFolder:
        print("making new folder, saving ID")
        folder = drive.CreateFile({'title' : "M4L-Timbre-Transfer-Folder", 'mimeType' : 'application/vnd.google-apps.folder'})
        folder.Upload()
        file_list = drive.ListFile({'q': "'root' in parents and trashed=false and title = 'M4L-Timbre-Transfer-Folder'"}).GetList()
        for file1 in file_list:
            # print("FOLDER", file1)
            print('title: %s, id: %s' % (file1['title'], file1['id']))
            txtfile = open("folderID.txt", "w")
            txtfile.write(str(file1['id']))
            txtfile.close()
    else:
        print("Folder exists, saving ID..")
        for file1 in existingFolder:
            print("FOLDER", file1)
            print('title: %s, id: %s' % (file1['title'], file1['id']))
            txtfile = open("folderID.txt", "w")
            txtfile.write(str(file1['id']))
            txtfile.close()



def setupPyDrive():
    global gauth, drive
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)

counter = 0
def clearFolder():
    global gdID
    file_list = drive.ListFile(
        {'q': "'" + gdID +"'" +  " in parents"}).GetList()
    for file1 in file_list:
        print('title: %s, id: %s' % (file1['title'], file1['id']))
        f1 = drive.CreateFile({'id': file1['id']})
        # dlfile.GetContentFile("dddsp" + str(counter) + '.wav')
        # f1.Delete()
    # https://stackoverflow.com/questions/3041986/apt-command-line-interface-like-yes-no-input
    print("You have some files in the folder, these need to be clear DELETE THE FILES ABOVE? ACTION CANNOT BE UNDONE: yes/no")
    yes = {'yes','y', 'ye', ''}
    no = {'no','n'}
    choice = input().lower()
    if choice in yes:
        for file1 in file_list:
            print('title: %s, id: %s' % (file1['title'], file1['id']), "DELETED")
            f1 = drive.CreateFile({'id': file1['id']})
            f1.Delete()
    elif choice in no:
        print('PLEASE SAY YES IF EMPTY, MIIGHT FUCK UP SHIT')

def notify(filePath):
    global client
    print("NOTIFYING!!!!", client, type(client))
    client.send_message("/notify", filePath)
    # client.send_message("/test", 1)


def downloadFile():
    global counter, latency
    while True:
        print("lookiing for", counter)
        file_list = drive.ListFile(
            {'q': "'" + gdID + "'" +  " in parents and trashed=false and title = '" + "ddspd" + str(counter) + ".wav'"}).GetList()
        for file1 in file_list:
            print('title: %s, id: %s' % (file1['title'], file1['id']))
            dlfile = drive.CreateFile({'id': file1['id']})
            dlfile.GetContentFile("ddsp" + str(counter) + '.wav')
        if os.path.isfile("ddsp" + str(counter) + ".wav"):
            print("FILE ", counter, " DOWNLOADED")
            print("TIME WAS ", latency - (int(time.time()) % 86400))
            notify(os.path.abspath("ddsp" + str(counter) + ".wav"))
            counter = counter + 1
            break
        else:
            # print("NOT FOUND")
            time.sleep(0.2)


def sendFile(unused_addr, fileName, model, octave, loudness, threshold, auto, autotune, quiet):

    print("sending:", unused_addr, fileName, model, octave, loudness, threshold, auto, autotune, quiet)
    global counter, gdID, latency
    latency = int(time.time()) % 86400

    # set settings to JSON-file, send to GD
    jsonString = '{"iteration":' + \
        str(counter) + ', "model": "' + str(model) + \
        '", "octave": ' + str(octave) + \
        ', "loudness":' + str(loudness) + \
        ', "threshold":' + str(threshold) +    \
        ', "auto":' + str(auto) + \
        ', "autotune":' + str(autotune) + \
        ', "quiet":' + str(quiet) + \
        ', "time":'  + str(int(time.time()) % 86400) + '}'
    testfile = drive.CreateFile(
            {'parents': [{'id': gdID}], 'title': 'settings' + str(counter) + '.json'})
    testfile.SetContentString(jsonString)
    testfile.Upload()


    # convert to 16000 sample rate
    data, sr = librosa.load(fileName, sr=16000)
    print("data", data)
    data = data.astype(np.float32)
    sf.write('send.wav', data, 16000, subtype='PCM_16')
    # send audio file to GD
    testfile = drive.CreateFile(
            {'parents': [{'id': gdID}], 'title': 'sendAudio' + str(counter) + '.wav'})
    testfile.SetContentFile('send.wav')
    testfile.Upload()
    downloadFile()


if __name__ == "__main__":
    # FOR AUTHENTICATIION
    # global gdID

    print("asdfasdf")
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", required=False, help="create GD folder")
    parser.add_argument("--ip", default="127.0.0.1",
      help="The ip of the OSC server")
    parser.add_argument("--port", type=int, default=5033,
      help="The port the OSC server is listening on")
    args = parser.parse_args()
    print("args", args)
    setupPyDrive()
    # createGDFolder()
    if (args.init):
        print("args.firstTime was:", args.init)
        # time.sleep(5)
        createGDFolder()
    txtfile = open("folderID.txt", "r")
    gdID = txtfile.read()
    # print("GD IS", gdID)
    clearFolder()
    # SET UP OSC server
    dispatcher = dispatcher.Dispatcher()
    dispatcher.map("/sendFile", sendFile)
    server = osc_server.ThreadingOSCUDPServer(
        ("localhost", 5034), dispatcher)
    print("Serving on {}".format(server.server_address))
    client = udp_client.SimpleUDPClient(args.ip, args.port)

    server.serve_forever()
