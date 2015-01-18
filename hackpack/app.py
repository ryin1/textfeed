import re
import requests, base64 
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
    if "everyblock" in body:
        textinput = body.replace('everyblock','')
        textinput = 'university city'#sent from sms
        metros = ['philly', 'denver', 'houston', 'boston', 'chicago']
        #find which metro it is in
        if textinput.isdigit():
            texttype = 'zipcodes'
            for metro in metros:
                everyblock_url = 'https://api.everyblock.com/content/%s/zipcodes'%metro
                r = requests.get(everyblock_url, headers = {'Authorization' : 'Token fc51e71739c072154f4f8d58ed4f9ec0770aee76'})
                return_data = json.loads(r.text)
                for i in return_data:
                    #print i
                    if textinput == i['name']:
                        #print textinput,'is in',metro
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
                        #print textinput,'is in',metro
                        metro_final = metro
                        textinput = textinput.replace(' ','-')
                        break
        #found the metro!
        everyblock_url = 'https://api.everyblock.com/content/%s/locations/%s/timeline/?schema=crime'%(metro_final, textinput)
        r = requests.get(everyblock_url, headers = {'Authorization' : 'Token fc51e71739c072154f4f8d58ed4f9ec0770aee76'})
        return_data = json.loads(r.text)
        output = ''
        count = 0
        for event in return_data['results']:
            date = event['pub_date']
            #date in good format
            date = date[5:7]+'/'+date[8:10]+'/'+date[2:4]
            #time: use dispatch time
            time = datetime.strptime(event['attributes']['dispatch_time'][:5], '%H:%M')
            time = time.strftime('%I:%M %p')
            output += event['title']+' on '+event['location_name']+' at '+date+', '+time+'. '
            count += 1
            if count == 2:
                break
        response.sms(output)
    else:
        response.sms('Text "everyblock" and your zip code or town to get a feed!')
    return str(response)

# Installation success page
@app.route('/')
def index():
    params = {
        'Voice Request URL': url_for('.voice', _external=True),
        'SMS Request URL': url_for('.sms', _external=True)
    return render_template('index.html', params=params,
                           configuration_error=None)
