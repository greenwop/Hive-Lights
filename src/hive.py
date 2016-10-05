import datetime
from astral import *
import pytz
import requests
import json
from pprint import pprint
import time
import simplejson

#global vars
username= None
password= None
thermostat_id= None
apikey = None
DEBUG=False
l = None
data= None
now = None
l = Location(info=("London","UK",51.5074, 0.1278, "Europe/London"))

#payload constants
ON_PAYLOAD= '{"nodes":[{"attributes":{"state":{"targetValue":"ON"}}}]}'
OFF_PAYLOAD= '{"nodes":[{"attributes":{"state":{"targetValue":"OFF"}}}]}'

#sends the username/password combo to get an apikey
def getApiKey():
	global apikey
	if apikey is None:
		#gets a new apikey
		keys = {'username':username,'password':password,'caller':'web'}
		r = requests.post("https://api-prod.bgchprod.info:8443/api/login",params=keys)
		apikey= r.json()['ApiSession']

	return apikey

#queries the hive api to get whether the specifed light is on or not
def isLightOn(light_id):

	#sends the request to get the light's status
	headers= {'X-Omnia-Access-Token':getApiKey(),'X-AlertMe-Client':'Web','Accept':'application/vnd.alertme.zoo-6.4+json'}
	r = requests.get("https://api-prod.bgchprod.info/omnia/nodes/"+light_id,headers=headers)

	#presumes light is on
	lightOn= True

	#gets the light's status from the returned JSON and tests if it is off or not.
	if str(r.json()['nodes'][0]['attributes']['state']['reportedValue']) == 'OFF':
		lightOn= False

	return lightOn

#work out whether the current time is after sunrise but before sunset
def isDayTime():
	#now = now.replace(hour=23, minute=10)
	daytime= False

	#extract the sunrise/sunset times adds/substracts 30 minutes from these times to account for dawn/dusk
	sunrise= getSunrise()
	sunset= getSunset()

	#if the current time is between sunrise and sunset then its daytime
	if now >= sunrise and now <= sunset:
		daytime=True

	return daytime

#calculates the sunrise time and adds 30 minutes to account for it still being dark
def getSunrise():
	return l.sunrise() + datetime.timedelta(minutes=30)

#calculates the sunset time and substracts 30 minutes to account for it getting dark
def getSunset():
	return l.sunset() - datetime.timedelta(minutes=30)

#gets the time the device was last modified from the server
def getRemoteModifiedTime(light_id):
	#sends the request to get the light's status
	headers= {'X-Omnia-Access-Token':getApiKey(),'X-AlertMe-Client':'Web','Accept':'application/vnd.alertme.zoo-6.4+json'}
	r = requests.get("https://api-prod.bgchprod.info/omnia/nodes/"+light_id,headers=headers)

	#presumes light is on
	return r.json()['nodes'][0]['attributes']['state']['reportReceivedTime']

#saves the reported time from the server locally
def saveModifiedTime(light_id, timestamp, lightOn):
	# now write output to a file
	lightFile = open(light_id+".json", "w")
	# magic happens here to make it pretty-printed
	output= {'id':light_id,'modified':timestamp, 'lightOn':lightOn}
	data= json.dumps(output)
	lightFile.write(simplejson.dumps(simplejson.loads(data), indent=4, sort_keys=True))
	lightFile.close()

#reads the time the script last modified the device
def getLocalModifiedTime(light_id):
	try:
		with open(light_id+'.json') as json_data:
			d = json.load(json_data)
			return d['modified']
	except IOError:
		return getRemoteModifiedTime(light_id)

#returns true if the device was modified outside of this script and someone has turned the light on/off with via the app or dashboard
def isOverridden(light_id):
	#gets the time the device was last modified by the script
	local_update= datetime.datetime.fromtimestamp(getLocalModifiedTime(light_id)/1000.0)

	#gets the time the device was last modified by anything
	remote_update= datetime.datetime.fromtimestamp(getRemoteModifiedTime(light_id)/1000.0)

	#if device has been modified since this script last modified it
	if remote_update > local_update:
		print "isOverridden"
		return True

	return False

#sends the request to turn the specified light on or off (contained within the payload provided)
def turnLightOnOrOff(light_id, payload):
	headers= {'X-Omnia-Access-Token':getApiKey(),'X-AlertMe-Client':'Web','Accept':'application/vnd.alertme.zoo-6.4+json','Content-Type':'application/json'}
	r = requests.put("https://api-prod.bgchprod.info/omnia/nodes/"+light_id,headers=headers, data=payload)

#sends a request to get the state of the hive thermostat
def isHolidayModeEnabled(thermostat_id):
	headers= {'X-Omnia-Access-Token':getApiKey(),'X-AlertMe-Client':'Web','Accept':'application/vnd.alertme.zoo-6.4+json'}
	r = requests.get("https://api-prod.bgchprod.info/omnia/nodes/"+thermostat_id,headers=headers)

	#extracts the reported value for holiday mode attribute
	return r.json()['nodes'][0]['attributes']['holidayMode']['reportedValue']['enabled']

#load all the global values from the json config and return the schedule array fro processing
def loadJSON():
	global username, password, thermostat_id,data, now
	now = datetime.datetime.now(pytz.timezone('Europe/London'))
	#reads in the JSON array containing the lights schedule
	json_data=open("schedule.json").read()
	data = json.loads(json_data)
	username= data['username']
	password= data['password']
	thermostat_id= data['thermostat_id']
	return data['schedule']

def main():
	schedule = loadJSON()
	#for each light in the schedule
	for i in schedule:
		#gets the unique id for the current light
		light_id = i['id']

		#determines the current day of week so we can get the right entry in the schedule
		
		#now = now.replace(hour=23, minute=10)
		day= now.strftime("%A")
		day_schedule= i[day]

		#builds the on and off times from the schedule
		onAfter= now.replace(hour=day_schedule['on']['hour'], minute=day_schedule['on']['minute'], second=0, microsecond=0)
		offAfter= now.replace(hour=day_schedule['off']['hour'], minute=day_schedule['off']['minute'], second=0, microsecond=0)

		#gets all the values to determine what to do
		lightOn= isLightOn(light_id)
		modifiedTime= getLocalModifiedTime(light_id)
		modifiedDateTime= datetime.datetime.utcfromtimestamp(modifiedTime/1000.0).replace(tzinfo=pytz.timezone('Europe/London'))
		dayTime= isDayTime()
		holidayMode= isHolidayModeEnabled(thermostat_id)

		if DEBUG:
			print "Modified time: "+str(modifiedDateTime)
			print "isLighOn: "+str(lightOn)
			print "Sunrise: "+str(getSunrise())
			print "Sunset: "+str(getSunset())
			print "OffAfter: "+str(offAfter)
			print "OnAfter: "+str(offAfter)
			print "Daytime: "+str(dayTime)

		#if in holiday mode and we've left the lights on...
		if holidayMode and lightOn:
			print "Holiday Mode!"
			turnLightOnOrOff(light_id,OFF_PAYLOAD)
			saveModifiedTime(light_id,modifiedTime, False)

		#if not in holiday mode  and current time is after the earliest on time and before the latest off time and the sun isn't up.
		elif not holidayMode and now>=onAfter and now<=offAfter and not dayTime:
			#if the light is currently off
			if not lightOn:
				print "Turn light on please!"
				#turns the light on
				turnLightOnOrOff(light_id,ON_PAYLOAD)
				saveModifiedTime(light_id,modifiedTime, True)
			else:
				#light is already on
				print "Light is on or overridden - do nothing"
		#current time is in the day time so light should be off
		else:
			#if the light is on
			if (lightOn and not isOverridden(light_id)) or (lightOn and modifiedDateTime<onAfter and now > getSunrise()) or (lightOn and modifiedDateTime<getSunset() and now > offAfter):
				print "Turn the light off please"
				#need to turn the light off
				turnLightOnOrOff(light_id,OFF_PAYLOAD)
				saveModifiedTime(light_id,modifiedTime, False)
			else:
				#light is already off
				print "Light is off or has been overriden - do nothing"

if __name__ == "__main__":
	main()