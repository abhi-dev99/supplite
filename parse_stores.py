import re
import json
import time
import urllib.request
import urllib.parse

def parse_stores():
    addresses = []
    
    with open('data/wsi stores.txt', 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.read().splitlines() if line.strip()]

    for i, line in enumerate(lines):
        if line.startswith('Phone:'):
            city_state = lines[i-1]
            parts = city_state.split(',')
            if len(parts) == 2:
                city = parts[0].strip()
                state = parts[1].strip()[:2]
                addresses.append({
                    "name": f"WSI {city}",
                    "city": city,
                    "state": state,
                    "query": f"{city}, {state}, USA"
                })

    print(f"Parsed {len(addresses)} unique stores!")
    
    cached_coords = {}
    final_stores = []
    
    unique_cities = {}
    for a in addresses:
        if a['query'] not in unique_cities:
            unique_cities[a['query']] = a
            
    print(f"Reduced to {len(unique_cities)} unique city clusters for geocoding.")

    for query, store in unique_cities.items():
        if query in cached_coords:
            continue
            
        url = "https://nominatim.openstreetmap.org/search?q=" + urllib.parse.quote(query) + "&format=json&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'supplite-hackathon-mapper'})
        
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                if data and len(data) > 0:
                    store['coordinates'] = [float(data[0]['lon']), float(data[0]['lat'])]
                    cached_coords[query] = store['coordinates']
                    store['type'] = 'STORE'
                    store['status'] = 'Operational'
                    
                    # Tie to nearest DC visually
                    store['suppliedBy'] = 'Regional Hub'
                    final_stores.append(store)
            time.sleep(1) # respect Nominatim rules
        except Exception as e:
            print(f"Error geocoding {query}: {e}")
            
    with open('data/parsed_stores.json', 'w') as out:
        json.dump(final_stores, out, indent=2)
        
    print(f"Successfully geocoded {len(final_stores)} stores and saved to data/parsed_stores.json")

if __name__ == '__main__':
    parse_stores()
