import requests
import code

geo_url = 'https://maps.googleapis.com/maps/api/directions/json'
KEY = 'AIzaSyAYVaWfdsXzPpuwitbDAg9g_9URCmvhQD8'
r = requests.get(geo_url, params={'origin': '11 Cedar Dr Stony Brook', 'destination': '20 nadworny lane', 'key': KEY})
data = r.json()

code.interact(local=locals())