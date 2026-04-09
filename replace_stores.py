import json

def replace_stores():
    with open('data/parsed_stores.json', 'r') as f:
        stores = json.load(f)
        
    for s in stores:
        # Map the visual styling markers matching the old array
        s['id'] = s.get('name', 'WS Location')
        s['type'] = 'STORE'
        s['status'] = 'Operational'
        s['suppliedBy'] = 'Regional Hub'

    # Read data.js
    with open('frontend/src/data.js', 'r') as f:
        content = f.read()

    # Find where export const wsStores = ... begins
    import re
    # We want to replace from "export const wsStores = [" or "export const wsStores = Array.from"
    # to the end or to the next export
    pattern = re.compile(r'export const wsStores = .*?\n}\);', re.DOTALL)
    
    # Check if we find the Array.from version
    if not pattern.search(content):
        # Maybe it's a bracket version
        pattern = re.compile(r'export const wsStores = \[.*?\];', re.DOTALL)
        
    # We serialize the python stores dict to a JS array string
    js_array_str = "export const wsStores = " + json.dumps(stores, indent=2) + ";"
    
    new_content = pattern.sub(js_array_str, content)
    
    with open('frontend/src/data.js', 'w') as f:
        f.write(new_content)
        
    print("Injected successfully!")

if __name__ == '__main__':
    replace_stores()
