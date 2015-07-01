import requests
import praw
import json
from datetime import datetime

API_KEY = 'fc51e71739c072154f4f8d58ed4f9ec0770aee76'

def text_feed(body):

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
                    print(data)
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
            print('not found error')
            return 'not found', 'error'
        
        metro, location = find_metro(' '.join(body_split[1:]))
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
            #print 'event', event
            date = event['item_date']
            #date in good format
            date = date[5:7]+'/'+date[8:10]+'/'+date[2:4]
            #time: find the time
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

    # body: Input string
    # body = 'everyblock 11790'

    body_split = body.lower().split()

    if body_split[0] == 'directions':
        # TO-DO: Maps
        pass
    elif body_split[0] == 'news':
        return news()
    elif body_split[0] == 'everyblock':
        return everyblock(body_split)
    return 'Try again in the correct format'

print(text_feed(('everyblock University City')))

                