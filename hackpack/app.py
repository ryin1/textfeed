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

# Declare and configure application
app = Flask(__name__, static_url_path='/static')
app.config.from_pyfile('local_settings.py')

API_KEY = os.environ.get('EVERYBLOCK_KEY', None)

# SMS Request URL
@app.route('/sms', methods=['GET', 'POST'])
def sms():
    response = twiml.Response()
    body = request.form['Body'].lower()

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


def news():
    '''Returns top 3 hot news stories fetched from news subreddit.'''
    r = praw.Reddit(user_agent='news_reader_textfeed')
    submissions = r.get_subreddit('news').get_hot(limit=3)
    return '. '.join(x.title for x in submissions)

def find_metro(s):
    '''Returns metro given a zipcode or town/city in one of the supported metros.'''
    if s.isdigit():
        everyblock_url = 'https://api.everyblock.com/content/{}/zipcodes'.format(met)
    else:
        everyblock_url = 'https://api.everyblock.com/content/{}/neighborhoods'.format(met)
    metros = ['philly', 'denver', 'houston', 'boston', 'chicago']
    for met in metros:
        r = requests.get(everyblock_url, headers={'Authorization': 'Token {}'.format(API_KEY)})
        data = json.loads(r.text)
        for i in data:
            if s.lower() == i['name'].lower():
                return met, s.lower().replace(' ', '-')
    return 'ERROR'

def everyblock(body_split):
    '''Returns everyblock crime news feed from Everyblock API.'''
    
    location = ' '.join(body_split[1:])
    metro = find_metro(location)
    if metro == 'ERROR':
        return 'EveryBlock couldn\'t determine your location. Try "everyblock [zipcode or town]" to get a crime feed for your area.'
    url = 'https://api.everyblock.com/content/{}/locations/{}/timeline/?schema=crime'.format(metro, location)
    r = requests.get(url, headers={'Authorization': 'Token {}'.format(API_KEY)})
    data = json.loads(r.text)
    if not r or data['count'] == 0:
        url = 'https://api.everyblock.com/content/{}/locations/{}/timeline/?schema=crime-reports'.format(metro, location)
        r = requests.get(url, headers={'Authorization': 'Token {}'.format(API_KEY)})
        data = json.loads(r.text)
    
    count = 0
    if 'count' in data or data['count'] != 0:
        output = ''
    timetypes = []
    for event in data['results']:
        date = event['item_date']
        date = '{}/{}/{}'.format(date[5:7], date[8:10], date[2:4])
        timetype = ''
        for time in ('dispatch_time', 'crime_time', 'occurrence_time', 'offense_time'):
            if time in event['attributes']:
                timetype = i
                break
        output += '{event} on {location} at {date}, {time}\n'.format(event=event['title'], location=event['location_name'], date=date, time=time)
        count += 1
        if count == data['count'] or count == 2:
            break
    return output