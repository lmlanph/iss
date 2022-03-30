import requests
import json
import time
import os
from datetime import datetime, timedelta
import psycopg2
import devmail_ISS as dm
from twilio.rest import Client

'''
background process, check API's, send text message if viewing conditions are ideal


59 reduce search area to 5, add some print statements back in for log
58 adds back cities to list, with timesent keys
57 add dm email with sun and cloud at TRUE EAST point?
56 expand sunset sunrise back to ast time (vs naut time)
56 add back in cloud/sunrise checks? adj to .75 cloud cover;

'''

# set any time in the past to initiate 'timesent', should then update with each send
cities = {
    'wenatchee': {'latitude': 47.4235, 'longitude': -120.3103, 'timesent': '2020-01-01 00:01:01.000000', 'passEast': '2020-01-01 20:29:49.418086'},
    'seattle': {'latitude': 47.6117, 'longitude': -122.3081, 'timesent': '2020-01-01 00:01:01.000000', 'passEast': '2020-01-01 20:29:49.418086'},
    'spokane': {'latitude': 47.6586, 'longitude': -117.4305, 'timesent': '2020-01-01 00:01:01.000000', 'passEast': '2020-01-01 20:29:49.418086'},
    'bellingham': {'latitude': 48.7529, 'longitude': -122.4920, 'timesent': '2020-01-01 00:01:01.000000', 'passEast': '2020-01-01 20:29:49.418086'},
    'walla walla': {'latitude': 46.0516, 'longitude': -118.2903, 'timesent': '2020-01-01 00:01:01.000000', 'passEast': '2020-01-01 20:29:49.418086'},
    'vancouver bc': {'latitude': 49.2947, 'longitude': -123.1457, 'timesent': '2020-01-01 00:01:01.000000', 'passEast': '2020-01-01 20:29:49.418086'},
    'portland': {'latitude': 45.5000, 'longitude': -122.6585, 'timesent': '2020-01-01 00:01:01.000000', 'passEast': '2020-01-01 20:29:49.418086'},
    'colville': {'latitude': 48.5460, 'longitude': -117.9157, 'timesent': '2020-01-01 00:01:01.000000', 'passEast': '2020-01-01 20:29:49.418086'},
    'CA los angeles': {'latitude': 34.0000, 'longitude': -118.0000, 'timesent': '2020-01-01 00:01:01.000000', 'passEast': '2020-01-01 20:29:49.418086'},
    'test': {'latitude': 40.5000, 'longitude': -74.0000, 'timesent': '2020-01-01 00:01:01.000000', 'passEast': '2020-01-01 20:29:49.418086'}
}

'''
tokyo 35.5, 139.5
madrid 40.5, -3.5 (7 hours ahead of wen?)
hawaii  19.5, -155.5, UTC-10
nyc  40.5, -74, UTC-4
fargo  47, -97, UTC-5
phoenix  33, -112, UTC-7(no daylight sav there)
jacksonville 30.5, -81.5, UTC-4

'''

psql_pass = os.environ.get('PSQL_PASS')
ds_key = os.environ.get('DS_KEY')
twilio_sid = os.environ.get('TWILIO_ACCOUNT_SID')
twilio_token = os.environ.get('TWILIO_AUTH_TOKEN')

client = Client(twilio_sid, twilio_token)


def ISS_writePos():  # write ISS pos to DB

    try:

        url_loc = "http://api.open-notify.org/iss-now.json"
        r1 = requests.get(url_loc)

        obj1 = json.loads(r1.text)

        ISSlat = obj1['iss_position']['latitude']
        ISSlon = obj1['iss_position']['longitude']

        connect = psycopg2.connect(
            database='iss',
            user='postgres',
            password=psql_pass
        )
        cursor = connect.cursor()
        cursor.execute('INSERT INTO isspos (lat, lon) VALUES (%s, %s)', (ISSlat, ISSlon))
        connect.commit()
        cursor.close()
        connect.close()

    except Exception as e:
        eType = type(e)
        e_message = f'the following error occurred in SECOND function:\ntype is: {eType}\ndetail is: {str(e)}'
        dm.mailMe(e_message)
        print(e_message)

def ISS_pos_E_timestamp(my_city):

    dist_spread = 5  # search area radius in degrees lat, lon

    url_loc = "http://api.open-notify.org/iss-now.json"
    r1 = requests.get(url_loc)

    obj1 = json.loads(r1.text)

    ISSlat = obj1['iss_position']['latitude']
    ISSlon = obj1['iss_position']['longitude']

    lat_delt = float(ISSlat) - my_city['latitude']
    lon_delt = float(ISSlon) - (my_city['longitude'] + 23.125)  # check for position due East (if W hemisphere)

    lastPassEast = datetime.strptime(my_city['passEast'], "%Y-%m-%d %H:%M:%S.%f")
    now = datetime.utcnow()
    diff = now - lastPassEast

    if diff > timedelta(minutes=120):  # make sure pass wasn't updated just this last pass 90 min ago--otherwise, may overwrite and never trigger msg?

        if abs(lat_delt) < dist_spread and abs(lon_delt) < dist_spread:  # add timestamp to passEast
            print(f'TRUE EAST: {datetime.utcnow()}')
            my_city['passEast'] = datetime.strftime(datetime.utcnow(), "%Y-%m-%d %H:%M:%S.%f")


def ISS_pos(city):

    now = datetime.utcnow()
    then = datetime.strptime(cities[city]['passEast'], "%Y-%m-%d %H:%M:%S.%f")
    myDelta = now - then
    Delta1 = timedelta(minutes=88)
    Delta2 = timedelta(minutes=90)
    if Delta2 > myDelta > Delta1:
        return True
    else:
        return False


def cloud_cover(my_city):

    url_ds = f"https://api.darksky.net/forecast/{ds_key}/{my_city['latitude']},{my_city['longitude']}?exclude=[minutely,hourly,daily,alerts,flags]"
    r2 = requests.get(url_ds)
    obj2 = json.loads(r2.text)

    cloud_cover = obj2.get('currently', {}).get('cloudCover', 1.0)  # empty dict for first default, prevents fail for 2nd get()?

    if cloud_cover < 0.65:
        return True
    else:
        return False


def sunset_sunrise(my_city):
    '''
    TIME IN UTC
    params = {'lat': 47.4235, 'lng': -120.3103, 'formatted': 0}
    '''
    url_sunset = 'https://api.sunrise-sunset.org/json'

    utc = datetime.utcnow()

    params = {'lat': my_city['latitude'], 'lng': my_city['longitude'], 'formatted': '0'}
    r3 = requests.get(url_sunset, params=params)
    obj3 = json.loads(r3.text)

    sunrise = obj3['results']['sunrise']
    naut_twi_beg = obj3['results']['nautical_twilight_begin']
    sunset = obj3['results']['sunset']  # get times
    naut_twi_end = obj3['results']['nautical_twilight_end']

    sunriseSplit = sunrise.split('+')
    naut_twi_begSplit = naut_twi_beg.split('+')
    sunsetSplit = sunset.split('+')  # splt off the 00:00 UTC offset--not needed, can't format with %z
    naut_twi_endSplit = naut_twi_end.split('+')

    sunrise_dt = datetime.strptime(sunriseSplit[0], '%Y-%m-%dT%H:%M:%S')
    naut_twi_beg_dt = datetime.strptime(naut_twi_begSplit[0], '%Y-%m-%dT%H:%M:%S')
    sunset_dt = datetime.strptime(sunsetSplit[0], '%Y-%m-%dT%H:%M:%S')  # convert to datetime objects
    naut_twi_end_dt = datetime.strptime(naut_twi_endSplit[0], '%Y-%m-%dT%H:%M:%S')

    print(f'{naut_twi_beg_dt.time()}___{utc.time()}___{sunrise_dt.time()}\n{sunset_dt.time()}___{utc.time()}___{naut_twi_end_dt.time()}')

    if naut_twi_beg_dt.time() < utc.time() < sunrise_dt.time():
        return True
    elif sunset_dt.time() < utc.time() < naut_twi_end_dt.time():
        return True
    else:
        return False


def getSignups():

    connect = psycopg2.connect(
        database='iss',
        user='postgres',
        password=psql_pass
    )
    cursor = connect.cursor()
    cursor.execute("SELECT fname, phone, passes, time, city FROM signup")
    data = cursor.fetchall()
    cursor.close()
    connect.close()

    return data


def subPasses(currPhone):  # subtract a pass from db
    connect = psycopg2.connect(
        database='iss',
        user='postgres',
        password=psql_pass
    )
    cursor = connect.cursor()
    cursor.execute("UPDATE signup SET passes = passes - 1 WHERE phone = %s", (currPhone,))
    connect.commit()
    cursor.close()
    connect.close()


# need check to keep from sending 4 messages in 2 minutes? see ISS_pos window e.g. 88 to 90 delta
def checkLastSent(my_city):
    lastSent = datetime.strptime(cities[my_city]['timesent'], "%Y-%m-%d %H:%M:%S.%f")
    wait_till = lastSent + timedelta(minutes=45)  # check to see if the city has been sent a msg in last n minutes

    if datetime.utcnow() > wait_till:
        return True
    else:
        return False


# update timesent in dict
def updateLastSent(my_city):
    cities[my_city]['timesent'] = datetime.strftime(datetime.utcnow(), "%Y-%m-%d %H:%M:%S.%f")


def is_pm():
    noon = datetime(2020, 1, 1, 12, 0, 0)
    now = datetime.utcnow()
    localNow = now - timedelta(hours=8)  # get local time
    if localNow.time() < noon.time():
        return False
    else:
        return True


def dawnDusk(ampmChoice):
    if ampmChoice == 3:
        return True
    if ampmChoice == 1 and is_pm():
        return True
    if ampmChoice == 2 and not is_pm():
        return True
    else:
        return False  # probably not needed?


# send a text message
def message():

    # loop through each city in dict
    for city in cities:

        current_city_coords = cities[city]  # get city from dict above

        # print(f"\ncurrent city is: {city} ...{current_city_coords}")

        try:

            ISS_pos_E_timestamp(current_city_coords)  # if ISS due East of city, add timestamp to city

            if ISS_pos(city) and checkLastSent(city):  # check if ISS was due East last orbit... and city hasn't been texted last 45 minutes...
                print('ISS_pos TRUE, checking now for cloud_cover and sunset_sunrise...')
                print(cloud_cover(current_city_coords))
                print(sunset_sunrise(current_city_coords))

                if cloud_cover(current_city_coords) and sunset_sunrise(current_city_coords):

                    for i in getSignups():  # look at each user record

                        if i[4] == city and i[2] > 0 and dawnDusk(i[3]):  # if the current city is equal to the user's city

                            if i[2] == 1:
                                body = f"{i[0]}! look for ISS overhead in a couple minutes!? http://www.spacewa.com ...last pass, want to add more? head back to /signup"
                            else:
                                body = f"{i[0]}! look for ISS overhead in a couple minutes!? http://www.spacewa.com"

                            num = '+1' + i[1]
                            client.messages.create(  # send user a message
                                to=num,
                                from_='+12062086687',
                                body=body
                            )

                            subPasses(i[1])  # subtract one pass from DB

                    updateLastSent(city)  # update the dict with current time, prevent multiple texts

        except Exception as e:
            eType = type(e)
            e_message = f'THE FOLLOWING ERROR OCCURRE//D\ntype is: {eType}\ndetail is: {str(e)}'
            dm.mailMe(e_message)
            print(e_message)


def main():

    count = 0

    while True:  # infite loop with sleep, cancel manually

        if count % 3 == 0:  # write pos every nth sleep to DB
            ISS_writePos()

        message()

        time.sleep(30)

        count += 1


if __name__ == "__main__":

    main()
