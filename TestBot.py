import time
import datetime
import telepot
import psutil
import os
import socket
import pyowm
import googlemaps
import geocoder
from subprocess import PIPE, Popen
from bs4 import BeautifulSoup
from lxml import html
from nsetools import Nse
import csv
import urllib2
import requests
import ConfigParams
import network_scanner as scanner

def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)

    file_id  =  ""
    chat_id = msg['chat']['id']
    command = ""
    user = ""

    if(content_type == "text"):
        chat_id = msg['chat']['id']
        command = msg['text']
        print("in text mode")
        user = msg['from']['first_name']
        print("Got command: %s" %command)

        if command == 'time':
            bot.sendMessage(chat_id, str(datetime.datetime.now()))

        #determining reply message based on the hourof day
        elif command == 'Hi' or command == 'hi' or command == 'HI' or command == 'hI':     #Hi Query
            replyMessage = "Hi "+ user + " "
            greeting = "It is sleeping time you still awake"
            hour = int(datetime.datetime.strftime(datetime.datetime.now(), '%H'))
            #print(hour)
            if(hour >= 4 and hour < 12):
                greeting = "Good Morning"
            elif(hour >= 12 and hour < 16):
                greeting = "Good Afternoon"
            elif(hour >= 16 and hour < 20):
                greeting = "Good Evening"

            replyMessage = replyMessage+greeting
            bot.sendMessage(chat_id, replyMessage)

        #gives various details of raspberry pi
        elif command.lower() == "How are you".lower():      #Health Query
            print("In Health Query")
            cpu_temparature = get_cpu_temparature()
            cpu_usage = psutil.cpu_percent()
            ram = psutil.virtual_memory()
            ram_total = ram.total / 2**20       # MiB.
            ram_used = ram.used / 2**20
            ram_free = ram.free / 2**20
            ram_percent_used = ram.percent

            disk = psutil.disk_usage('/')
            disk_total = disk.total / 2**30     # GiB.
            disk_used = disk.used / 2**30
            disk_free = disk.free / 2**30
            disk_percent_used = disk.percent

            message = "I am doing as \nCPU Temparature "+str(cpu_temparature)+"C \nCPU Usage "+str(cpu_usage)+" \nRam Percent Used "+str(ram_percent_used)+" \nFree Disk Space "+ str(disk_free) + "Gb"
            bot.sendMessage(chat_id, message)

        #sends the local ip address and the wifi name to which it is connected to
        elif command.lower() == "Where are you".lower():
            print("telling where am I")
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((ConfigParams.google_domain,80))
            ipaddr = s.getsockname()[0]
            wifi = Wireless('wlan0')
            wifiname = wifi.getEssid()

            message = "I am connected on "+ipaddr+" \nto WiFi "+wifiname
            bot.sendMessage(chat_id, message)
        elif command.lower()=="coming up cricket":
            print("fetching upcoming matches")

        #if below command is cricket then it will fetch scrores from cricbuzz page
        elif command.lower() == "cricket".lower():
            print("Fetching Cricket Scores ...")
            page = requests.get(ConfigParams.crc_buzz_url)
            tree = html.fromstring(page.content)
            #searching for required data
            allscoreslist=tree.xpath(ConfigParams.cric_buzz_path)
            allscores = []
            #for loop used to remove duplicate values may override actual existing values some time
            #todo
            for score in allscoreslist:
                if  score not in allscores:
                    allscores.append(score)
            message = ""
            teamscores = []
            #formatting data received for readability
            for score in allscoreslist:
                if score[0].isdigit():
                    message=message+(score+"\n")
                else:
                    if len(score)>6:
                        score=score+"\n"
                        message=message+score
                        message=message+"**************"+"\n"
                        if message not in teamscores:
                            teamscores.append(message)
                            message = ""
                        else:
                            print("Met matching values")
                            message = ""
                    else:
                        message=message+(score+"\t")

            bot.sendMessage(chat_id, "".join(teamscores))

        #used for downloading files uploaded to this bot
        elif command.lower().find("download") != -1:

            if command.split(".")[1] == "jpg" or command.split(".")[1] == "jpeg" or command.split(".")[1] == "png":
                try:
                    filename = '/home/pi/Scripts/photos/'+command.split(" ")[1]
                    document = open(r'/home/pi/Scripts/photos/'+command.split(" ")[1])
                except IOError:
                    bot.sendMessage(chat_id,"File not found")
            else:
                try:
                    filename = '/home/pi/Scripts/documents/'+command.split(" ")[1]
                    document = open(r'/home/pi/Scripts/documents/'+command.split(" ")[1])
                except IOError:
                    bot.sendMessage(chat_id,"File not found")

            bot.sendDocument(chat_id, document)

        #if message contains stocks key word then it tries to fetch company and sends to get nse stock code to get current price
        elif command.lower().split(":")[0]=="stocks":
            #variable for storing variable name
            company = command.split(":")[1]
            nse = Nse()
            all_codes = readCodesFile('StockCodes.csv', company)
            if bool(all_codes):
                codes = sorted(all_codes.keys())
                message = " "
                for code in codes:
                    message = message + code + " : " + str(nse.get_quote(all_codes[code])['lastPrice'])+"\n"
            else:
                message = "Stock not found"
            bot.sendMessage(chat_id, message)
        elif command.lower() == "scan local":
            message = scanner.get_available_devices_info()
        else:
            message = "My Boss asked me to stay silent rather giving false information"
            bot.sendMessage(chat_id, message)

    #if user sent message is of photo or video or document then below code is used to store it on raspberry pi and download later
    elif(content_type == "document" or content_type == "photo" or content_type == "video"):
        if content_type == "document":
            file_id = msg['document']['file_id']

            file_name = msg['document']['file_name']

        elif content_type == "photo":
            file_id = msg['photo'][-1]['file_id']

        elif content_type == "video":
            file_id = msg['video']['file_id']

        bot.getUpdates()
        filereceived= bot.getFile(file_id)

        filepath = filereceived['file_path']

        file_name, file_extension = os.path.splitext(filepath)

        if content_type == "document":
            bot.download_file(file_id, "/home/pi/Scripts/"+file_name+file_extension)
            bot.sendMessage(chat_id, "Received and stored your file "+file_name)
        elif content_type == "photo":
            bot.download_file(file_id, "/home/pi/Scripts/"+file_name+file_extension)
            bot.sendMessage(chat_id, "Received and stored your photo "+file_name)
        elif content_type == "video":
            bot.download_file(file_id, "/home/pi/Scripts/"+file_name+file_extension)
            bot.sendMessage(chat_id, "Received and stored your video "+file_name)

    #if user sent message is location then below code is executed
    elif content_type == 'location':
        location = msg['location']

        lat = location['latitude']
        lon = location['longitude']

        owm = pyowm.OWM(ConfigParams.open_weather_key)
        observation = owm.weather_at_coords(lat, lon)
        weather = observation.get_weather()
        location = observation.get_location()

        gmaps = googlemaps.Client(key=ConfigParams.google_key)
        geo_loc = str(lat), str(lon)
        g = geocoder.google(geo_loc,method='reverse')

        message = "***Weather&Location Statistics***"
        message = message+"\nCity : "+location.get_name()+"\nState : "+g.state+"\nPostalCode : "+g.postal+"\nTemp Max : "+str(weather.get_temperature('celsius')['temp_max'])+"\nTemp Min : "+str(weather.get_temperature('celsius')['temp_min'])+" \nStatus : "+weather.get_detailed_status()+"\nSunRise : "+weather.get_sunrise_time('iso')
        message = message+"\nSunSetTime : "+weather.get_sunset_time('iso')+"\n"

        bot.sendMessage(chat_id, message)

#to get cpu temparature of raspberry pi
def get_cpu_temparature():
    process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE)
    output, error = process.communicate()
    return float(output[output.index('=') +1:output.rindex("'")])

#download the file which is present in uploaded from this bot application later
def download_file(download_url, dest):
    response = urllib2.urlopen(download_url)
    file = open(dest, 'w')
    file.write(response.read())
    file.close()
    print("Completed")

#read codes of stock companies registered in NSE based on company name
def readCodesFile(fileName, inputName):
    allcodes = {}
    with open(fileName) as csvFile:
        csvReader = csv.DictReader(csvFile)
        for row in csvReader:
            targets = row['companyname'].split(" ")
            var = 0
            while len(targets) > var :
                if inputName.lower() == (targets[var]).lower():
                    allcodes[row['companyname']] = row['code']
                    break;
                var = var + 1

    return allcodes

#algorithm to find the closest words even though spellings are wrong
def levenshteinDistance(s, t):
	if not s: return len(t)
	if not t: return len(s)
	if s[0] == t[0]: return levenshteinDistance(s[1:], t[1:])
	l1 = levenshteinDistance(s, t[1:])
	l2 = levenshteinDistance(s[1:], t)
	l3 = levenshteinDistance(s[1:], t[1:])
	return 1 + min(l1, l2, l3)


bot = telepot.Bot(ConfigParams.telegram_key)
bot.message_loop(handle)
print("I am listening ...")

while 1:
    time.sleep(10)
