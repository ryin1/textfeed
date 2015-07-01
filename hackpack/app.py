import re
import requests
import json
import os
import praw
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

API_KEY = os.environ.get('EVERYBLOCK_KEY', None)

# Voice Request URL
@app.route('/voice', methods=['GET', 'POST'])
def voice():
    response = twiml.Response()
    response.say("Supported services: Everyblock, News, Maps. Version 1.1")
    return str(response)

# SMS Request URL
@app.route('/sms', methods=['GET', 'POST'])
def sms():
    response = twiml.Response()
    body = request.form['Body'].lower()

    def news():
        '''Returns top 3 hot news stories fetched from news subreddit.'''
        r = praw.Reddit(user_agent='news_reader_textfeed')
        submissions = r.get_subreddit('news').get_hot(limit=3)
        return '. '.join(x.title for x in submissions)

    def everyblock(body_split):
        '''Returns everyblock crime news feed from Everyblock API.'''
        # print(body_split)
        def find_metro(s):
            # print(s)
            if s.isdigit():
                for met in ('philly', 'denver', 'houston', 'boston', 'chicago'):
                    everyblock_url = 'https://api.everyblock.com/content/{}/zipcodes'.format(met)
                    r = requests.get(everyblock_url, headers={'Authorization': 'Token {}'.format(API_KEY)}) # want to keep key private!!!
                    data = json.loads(r.text)
                    for i in data:
                        if s == i['name']:
                            return met, s
            else:
                for met in ('philly', 'denver', 'houston', 'boston', 'chicago'):
                    everyblock_url = 'https://api.everyblock.com/content/{}/neighborhoods'.format(met)
                    r = requests.get(everyblock_url, headers={'Authorization': 'Token {}'.format(API_KEY)}) # want to keep key private!!!
                    data = json.loads(r.text)
                    print(s)
                    for i in data:
                        if s.title() == i['name']:
                            return met, s.lower().replace(' ', '-')
            return 'ERROR', 'not found'
        
        metro, location = find_metro(' '.join(body_split[1:]))
        if metro == 'ERROR':
            return 'EveryBlock couldn\'t determine your location. Try "everyblock [zipcode or town]" to get a crime news feed for your area.'
        everyblock_url = 'https://api.everyblock.com/content/{}/locations/{}/timeline/?schema=crime'.format(metro, location)
        r = requests.get(everyblock_url, headers = {'Authorization': 'Token {}'.format(API_KEY)})
        data = json.loads(r.text)
        if not r or data['count'] == 0:
            everyblock_url = 'https://api.everyblock.com/content/{}/locations/{}/timeline/?schema=crime-reports'.format(metro, location)
            r = requests.get(everyblock_url, headers = {'Authorization': 'Token {}'.format(API_KEY)})
            data = json.loads(r.text)
        
        count = 0
        if 'count' in data or data['count'] != 0:
            output = ''
        #print data
        for event in data['results']:
            date = event['item_date']
            date = date[5:7]+'/'+date[8:10]+'/'+date[2:4]
            timetype = ''
            for i in ('dispatch_time', 'crime_time', 'occurrence_time', 'offense_time'):
                if i in event['attributes']:
                    timetype = i
                    break
            time = datetime.strptime(event['attributes'][timetype][:5], '%H:%M').strftime('%I:%M %p')
            output += '{event} on {location} at {date}, {time}\n'.format(event=event['title'], location=event['location_name'], date=date, time=time)
            count += 1
            if count == data['count'] or count == 2:
                break
        return output

    body_split = body.lower().split()
    if body_split[0] == 'directions':
        # TO-DO: Maps
        pass
    elif body_split[0] == 'news':
        output = news()
        response.sms(output)
    elif body_split[0] == 'everyblock':
        output = everyblock(body_split)
        response.sms(output)
    else:
        response.sms('Text options:\n"everyblock [zipcode or town/city]": crime news feed for your area\n"news": hottest news stories')
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
