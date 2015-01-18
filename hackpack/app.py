import re
import requests
import json
from datetime import datetime

from flask import Flask
from flask import render_template
from flask import url_for
from flask import request

from twilio import twiml
from twilio.util import TwilioCapability

# Declare and configure application
app = Flask(__name__, static_url_path='/static')
app.config.from_pyfile('local_settings.py')


# Voice Request URL
@app.route('/voice', methods=['GET', 'POST'])
def voice():
    response = twiml.Response()
    response.say("Congratulations! You deployed the Twilio Hackpack "
                 "for Heroku and Flask.")
    return str(response)


# SMS Request URL
@app.route('/sms', methods=['GET', 'POST'])
def sms():
    response = twiml.Response()
    body = request.form['Body']
    metro_final = ''
    output = 'Nothing was found.'
    if "everyblock" in body:
        textinput = body.replace('everyblock ','')
        metros = ['philly', 'denver', 'houston', 'boston', 'chicago']
        #find which metro it is in
        #print textinput, type(textinput)
        if textinput.isdigit():
            print 'textinput is digit'
            texttype = 'zipcodes'
            for metro in metros:
                everyblock_url = 'https://api.everyblock.com/content/%s/zipcodes'%metro
                print everyblock_url
                r = requests.get(everyblock_url, headers = {'Authorization' : 'Token fc51e71739c072154f4f8d58ed4f9ec0770aee76'})
                return_data = json.loads(r.text)
                for i in return_data:
                    if textinput == i['name']:
                        metro_final = metro
                        break
        else:
            texttype = 'neighborhoods'
            for metro in metros:
                everyblock_url = 'https://api.everyblock.com/content/%s/neighborhoods'%metro
                #print 'trying: ',everyblock_url
                r = requests.get(everyblock_url, headers = {'Authorization' : 'Token fc51e71739c072154f4f8d58ed4f9ec0770aee76'})

                return_data = json.loads(r.text)
                for i in return_data:
                    if textinput.title() == i['name']:
                        print textinput,'is in',metro
                        metro_final = metro.lower()
                        textinput = textinput.lower().replace(' ','-')
                        break
        #found the metro!
        if metro_final != '':
            everyblock_url = 'https://api.everyblock.com/content/%s/locations/%s/timeline/?schema=crime'%(metro_final, textinput)
            #everyblock_url = 'https://api.everyblock.com/content/%s/schemas/'%metro_final
            print everyblock_url
            r = requests.get(everyblock_url, headers = {'Authorization' : 'Token fc51e71739c072154f4f8d58ed4f9ec0770aee76'})
            return_data = json.loads(r.text)
            if not r or return_data['count'] == 0:
                everyblock_url = 'https://api.everyblock.com/content/%s/locations/%s/timeline/?schema=crime-reports'%(metro_final, textinput)
                r = requests.get(everyblock_url, headers = {'Authorization' : 'Token fc51e71739c072154f4f8d58ed4f9ec0770aee76'})
                #print everyblock_url
                return_data = json.loads(r.text)
                #print return_data
            
            count = 0
            #print return_data, type(return_data)
            #print 'count' in return_data
            #print return_data['count']
            if 'count' in return_data or return_data['count'] != 0:
                output = ''
            #print return_data
            for event in return_data['results']:
                #print 'event', event
                date = event['item_date']
                #date in good format
                date = date[5:7]+'/'+date[8:10]+'/'+date[2:4]
                #time: find the time
                timetype = ''
                if 'dispatch_time' in event['attributes']:
                    timetype = 'dispatch_time'
                elif 'crime_time' in event['attributes']:
                    timetype = 'crime_time'
                elif 'occurrence_time' in event['attributes']:
                    timetype = 'occurrence_time'
                elif 'offense_time' in event['attributes']:
                    timetype = 'offense_time'
                else:
                    print 'else'

                time = datetime.strptime(event['attributes'][timetype][:5], '%H:%M')
                #print 'time', time
                time = time.strftime('%I:%M %p')
                #print event
                output += event['title']+' on '+event['location_name']+' at '+date+', '+time+'. '
                count += 1
                if count == return_data['count'] or count == 2:
                    break
        response.sms(output)
    else:
        response.sms('Text "everyblock" and your zip code or town to get a feed!')
    return str(response)


# Twilio Client demo template
@app.route('/client')
def client():
    configuration_error = None
    for key in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_APP_SID',
                'TWILIO_CALLER_ID'):
        if not app.config.get(key, None):
            configuration_error = "Missing from local_settings.py: " \
                                  "{0}".format(key)
            token = None

    if not configuration_error:
        capability = TwilioCapability(app.config['TWILIO_ACCOUNT_SID'],
                                      app.config['TWILIO_AUTH_TOKEN'])
        capability.allow_client_incoming("joey_ramone")
        capability.allow_client_outgoing(app.config['TWILIO_APP_SID'])
        token = capability.generate()
    params = {'token': token}
    return render_template('client.html', params=params,
                           configuration_error=configuration_error)


@app.route('/client/incoming', methods=['POST'])
def client_incoming():
    try:
        from_number = request.values.get('PhoneNumber', None)

        resp = twiml.Response()

        if not from_number:
            resp.say("Your app is missing a Phone Number. "
                     "Make a request with a Phone Number to make outgoing "
                     "calls with the Twilio hack pack.")
            return str(resp)

        if 'TWILIO_CALLER_ID' not in app.config:
            resp.say(
                "Your app is missing a Caller ID parameter. "
                "Please add a Caller ID to make outgoing calls with Twilio "
                "Client")
            return str(resp)

        with resp.dial(callerId=app.config['TWILIO_CALLER_ID']) as r:
            # If we have a number, and it looks like a phone number:
            if from_number and re.search('^[\d\(\)\- \+]+$', from_number):
                r.number(from_number)
            else:
                r.say("We couldn't find a phone number to dial. Make sure "
                      "you are sending a Phone Number when you make a "
                      "request with Twilio Client")

        return str(resp)

    except:
        resp = twiml.Response()
        resp.say("An error occurred. Check your debugger at twilio dot com "
                 "for more information.")
        return str(resp)


# Installation success page
@app.route('/')
def index():
    params = {
        'Voice Request URL': url_for('.voice', _external=True),
        'SMS Request URL': url_for('.sms', _external=True),
        'Client URL': url_for('.client', _external=True)}
    return render_template('index.html', params=params,
                           configuration_error=None)
