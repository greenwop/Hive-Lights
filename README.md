# Hive-Lights
Replacement Hive schedule for active lights &amp; plugs that takes into account sunrise and sunset times. Also supports holiday mode. 

Need to modify schedule.json with your Hive username/password and also thermostat_id (this is used to determine whether holiday mode is enabled).

JSON array schedule should be updated and extended for your preferences including the id for each device you want controlled by this script. Can then specify the on/off times for each day of the week, devices will only be turned on if sun hasn't risen yet or set yet and the current time is between your preferred on/off time.

Script also takes into account if a device is switched on outside of daylight hours and won't switch the device back off.

If your heating is put into holiday mode the schedule will be ignored completely and no devices switched on during this time.

Relevant ids can be obtained via: curl 'https://api-prod.bgchprod.info/omnia/nodes' -X GET -H 'X-Omnia-Access-Token: XXXXXX' -H 'X-AlertMe-Client: Hive Web Dashboard' -H 'Accept: application/vnd.alertme.zoo-6.4+json' -H 'Content-Type: application/json'

Access token retrieved via: curl -X POST -d "username=USERNAME&password=PASSWORD&caller=web" https://api-prod.bgchprod.info:8443/api/login

Can run the script via a cron job (to execute 5 minutes is about right).