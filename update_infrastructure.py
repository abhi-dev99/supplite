import json
import time
import urllib.request
import urllib.parse
import re

def geocode(location_name):
    query = location_name + ", USA"
    url = "https://nominatim.openstreetmap.org/search?q=" + urllib.parse.quote(query) + "&format=json&limit=1"
    req = urllib.request.Request(url, headers={'User-Agent': 'supplite'})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data and len(data) > 0:
                print(f"Geocoded {location_name}")
                return [float(data[0]['lon']), float(data[0]['lat'])]
    except Exception as e:
        print(f"Error {location_name}: {e}")
    time.sleep(1)
    return None

def main():
    networks = []
    
    # 1. Dist Hubs
    hubs = ["Oakland, CA", "Denver, CO", "Lakeland, FL", "Pompano Beach, FL", "Boston, MA", "Columbus, OH"]
    for h in hubs:
        coords = geocode(h)
        if coords:
            networks.append({"name": h, "coordinates": coords, "type": "HUB", "radiusMiles": 200, "status": "Active"})
            
    # 2. HQ
    hq = "San Francisco, CA"
    coords = geocode(hq)
    if coords:
        networks.append({"name": "Global HQ - San Francisco", "coordinates": coords, "type": "HQ", "radiusMiles": 800, "status": "Active"})

    # 3. Distribution Centers
    dcs = ["City of Industry, CA", "Olive Branch, MS", "South Brunswick, NJ", "Memphis, TN", "Dallas, TX", "Braselton, GA", "Litchfield Park, AZ", "Fontana, CA", "Tracy, CA"]
    for dc in dcs:
        coords = geocode(dc)
        if coords:
            networks.append({"name": f"{dc.split(',')[0]} DC", "coordinates": coords, "type": "DC", "radiusMiles": 400, "status": "Active"})

    # 4. Manufacturing
    mfg = ["Tupelo, MS", "Claremont, NC"]
    for m in mfg:
        coords = geocode(m)
        if coords:
            networks.append({"name": f"{m.split(',')[0]} Mfg", "coordinates": coords, "type": "MFG", "radiusMiles": 150, "status": "Active"})

    # 5. Customer Care Centers
    care = ["Columbus, OH", "Braselton, GA", "Shafter, CA", "Oklahoma City, OK", "Las Vegas, NV", "The Colony, TX"]
    for c in care:
        coords = geocode(c)
        if coords:
            networks.append({"name": f"{c.split(',')[0]} Care Center", "coordinates": coords, "type": "CARE", "radiusMiles": 0, "status": "Active"})

    # Read data.js and replace export const distributionCenters = [...]
    with open('frontend/src/data.js', 'r') as f:
        content = f.read()

    pattern = re.compile(r'export const distributionCenters = \[.*?\];', re.DOTALL)
    js_array_str = "export const distributionCenters = " + json.dumps(networks, indent=2) + ";"
    
    new_content = pattern.sub(js_array_str, content)
    
    with open('frontend/src/data.js', 'w') as f:
        f.write(new_content)
    print("Infrastructure updated into data.js")

if __name__ == "__main__":
    main()
