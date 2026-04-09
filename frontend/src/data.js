export const mockSkus = [
  {
    id: "PB-BLANKET-42",
    name: "Pottery Barn Throw Blanket Cognac",
    brand: "Pottery Barn",
    category: "Bedding",
    stock: 6200,
    daysOfSupply: 34,
    riskLevel: "STOCKOUT_RISK",
    signal: "Search spike +840%",
    action: "Expedite Order"
  },
  {
    id: "PB-PILLOW-71",
    name: "Decorative Pillow Sage",
    brand: "Pottery Barn",
    category: "Decor",
    stock: 4200,
    daysOfSupply: 89,
    riskLevel: "OVERSTOCK_RISK",
    signal: "Search decline -23%",
    action: "Markdown Variant"
  },
  {
    id: "PB-BED-FRAME-33",
    name: "Bedroom Set King",
    brand: "Pottery Barn",
    category: "Furniture",
    stock: 800,
    daysOfSupply: 65,
    riskLevel: "WATCH",
    signal: "Housing permits +34%",
    action: "Pre-position 400"
  },
  {
    id: "WE-LAMP-19",
    name: "West Elm Table Lamp",
    brand: "West Elm",
    category: "Lighting",
    stock: 890,
    daysOfSupply: 65,
    riskLevel: "OK",
    signal: "Baseline",
    action: "None"
  }
];

export const mockChartData = [
  { name: 'Week -8', sales: 120, search: 12, permits: 100 },
  { name: 'Week -7', sales: 118, search: 11, permits: 102 },
  { name: 'Week -6', sales: 122, search: 13, permits: 105 },
  { name: 'Week -5', sales: 119, search: 10, permits: 101 },
  { name: 'Week -4', sales: 125, search: 14, permits: 110 },
  { name: 'Week -3', sales: 130, search: 15, permits: 115 },
  { name: 'Week -2', sales: 128, search: 22, permits: 114 },
  { name: 'Week -1', sales: 160, search: 45, permits: 120 },
  { name: 'Week 0', sales: 412, search: 89, permits: 121 },
];

export const geoClusters = Array.from({ length: 1800 }).map(() => {
  // Center roughly around massive logistics hubs/metros
  const centers = [
     { name: 'LA Port Authority', lng: -118.24, lat: 34.05, weight: 0.8, type: 'STOCKOUT_RISK' },
     { name: 'Northeast Corridor', lng: -74.00, lat: 40.71, weight: 1.2, type: 'WATCH' },
     { name: 'Dallas DC', lng: -96.79, lat: 32.77, weight: 1.5, type: 'OVERSTOCK_RISK' },
     { name: 'Chicago Rail Hub', lng: -87.62, lat: 41.87, weight: 1.0, type: 'WATCH' },
     { name: 'Seattle Port', lng: -122.33, lat: 47.60, weight: 0.5, type: 'WATCH' }
  ];
  const c = centers[Math.floor(Math.random() * centers.length)];
  
  // Create normally distributed spread tightly packed (no ocean spilling)
  const lngOff = (Math.random() - 0.5) * c.weight + (Math.random() - 0.5) * c.weight;
  const latOff = (Math.random() - 0.5) * (c.weight/1.2) + (Math.random() - 0.5) * (c.weight/1.2);
  
  return {
     hub: c.name,
     zipPrefix: String(Math.floor(Math.random() * 90000) + 10000),
     position: [c.lng + lngOff, c.lat + latOff],
     // Only 15% of nodes show extreme red alert
     risk: Math.random() < 0.15 ? 'STOCKOUT_RISK' : (Math.random() > 0.6 ? 'OVERSTOCK_RISK' : 'WATCH'),
     volume: Math.floor(Math.random() * 1200) + 50,
     delay: Math.floor(Math.random() * 14) + ' Days'
  };
});

export const distributionCenters = [
  {
    "name": "Oakland, CA",
    "coordinates": [
      -122.271356,
      37.8044557
    ],
    "type": "HUB",
    "radiusMiles": 200,
    "status": "Active"
  },
  {
    "name": "Denver, CO",
    "coordinates": [
      -104.984862,
      39.7392364
    ],
    "type": "HUB",
    "radiusMiles": 200,
    "status": "Active"
  },
  {
    "name": "Lakeland, FL",
    "coordinates": [
      -81.9498042,
      28.0394654
    ],
    "type": "HUB",
    "radiusMiles": 200,
    "status": "Active"
  },
  {
    "name": "Pompano Beach, FL",
    "coordinates": [
      -80.1247667,
      26.2378597
    ],
    "type": "HUB",
    "radiusMiles": 200,
    "status": "Active"
  },
  {
    "name": "Boston, MA",
    "coordinates": [
      -71.0578303,
      42.3588336
    ],
    "type": "HUB",
    "radiusMiles": 200,
    "status": "Active"
  },
  {
    "name": "Columbus, OH",
    "coordinates": [
      -83.0007065,
      39.9622601
    ],
    "type": "HUB",
    "radiusMiles": 200,
    "status": "Active"
  },
  {
    "name": "Global HQ - San Francisco",
    "coordinates": [
      -122.4075201,
      37.7879363
    ],
    "type": "HQ",
    "radiusMiles": 800,
    "status": "Active"
  },
  {
    "name": "City of Industry DC",
    "coordinates": [
      -117.9593061,
      34.0182252
    ],
    "type": "DC",
    "radiusMiles": 400,
    "status": "Active"
  },
  {
    "name": "Olive Branch DC",
    "coordinates": [
      -89.8295315,
      34.9617605
    ],
    "type": "DC",
    "radiusMiles": 400,
    "status": "Active"
  },
  {
    "name": "South Brunswick DC",
    "coordinates": [
      -74.5317663,
      40.3818728
    ],
    "type": "DC",
    "radiusMiles": 400,
    "status": "Active"
  },
  {
    "name": "Memphis DC",
    "coordinates": [
      -90.0517638,
      35.1460249
    ],
    "type": "DC",
    "radiusMiles": 400,
    "status": "Active"
  },
  {
    "name": "Dallas DC",
    "coordinates": [
      -96.7968559,
      32.7762719
    ],
    "type": "DC",
    "radiusMiles": 400,
    "status": "Active"
  },
  {
    "name": "Braselton DC",
    "coordinates": [
      -83.7626729,
      34.1092735
    ],
    "type": "DC",
    "radiusMiles": 400,
    "status": "Active"
  },
  {
    "name": "Litchfield Park DC",
    "coordinates": [
      -112.358124,
      33.4933796
    ],
    "type": "DC",
    "radiusMiles": 400,
    "status": "Active"
  },
  {
    "name": "Fontana DC",
    "coordinates": [
      -117.43433,
      34.0922947
    ],
    "type": "DC",
    "radiusMiles": 400,
    "status": "Active"
  },
  {
    "name": "Tracy DC",
    "coordinates": [
      -121.420139,
      37.7385507
    ],
    "type": "DC",
    "radiusMiles": 400,
    "status": "Active"
  },
  {
    "name": "Tupelo Mfg",
    "coordinates": [
      -88.7033859,
      34.2576067
    ],
    "type": "MFG",
    "radiusMiles": 150,
    "status": "Active"
  },
  {
    "name": "Claremont Mfg",
    "coordinates": [
      -81.1461917,
      35.7145776
    ],
    "type": "MFG",
    "radiusMiles": 150,
    "status": "Active"
  },
  {
    "name": "Columbus Care Center",
    "coordinates": [
      -83.0007065,
      39.9622601
    ],
    "type": "CARE",
    "radiusMiles": 0,
    "status": "Active"
  },
  {
    "name": "Braselton Care Center",
    "coordinates": [
      -83.7626729,
      34.1092735
    ],
    "type": "CARE",
    "radiusMiles": 0,
    "status": "Active"
  },
  {
    "name": "Shafter Care Center",
    "coordinates": [
      -119.273682,
      35.501461
    ],
    "type": "CARE",
    "radiusMiles": 0,
    "status": "Active"
  },
  {
    "name": "Oklahoma City Care Center",
    "coordinates": [
      -97.5170536,
      35.4729886
    ],
    "type": "CARE",
    "radiusMiles": 0,
    "status": "Active"
  },
  {
    "name": "Las Vegas Care Center",
    "coordinates": [
      -115.1484131,
      36.1674263
    ],
    "type": "CARE",
    "radiusMiles": 0,
    "status": "Active"
  },
  {
    "name": "The Colony Care Center",
    "coordinates": [
      -96.8863922,
      33.0890094
    ],
    "type": "CARE",
    "radiusMiles": 0,
    "status": "Active"
  }
];

export const wsStores = [
  {
    "name": "WSI Birmingham",
    "city": "Birmingham",
    "state": "AL",
    "query": "Birmingham, AL, USA",
    "coordinates": [
      -86.8024326,
      33.5206824
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Birmingham"
  },
  {
    "name": "WSI Mobile",
    "city": "Mobile",
    "state": "AL",
    "query": "Mobile, AL, USA",
    "coordinates": [
      -88.0437509,
      30.6913462
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Mobile"
  },
  {
    "name": "WSI Chandler",
    "city": "Chandler",
    "state": "AZ",
    "query": "Chandler, AZ, USA",
    "coordinates": [
      -111.841185,
      33.3062031
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Chandler"
  },
  {
    "name": "WSI Phoenix",
    "city": "Phoenix",
    "state": "AZ",
    "query": "Phoenix, AZ, USA",
    "coordinates": [
      -112.074141,
      33.4484367
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Phoenix"
  },
  {
    "name": "WSI Scottsdale",
    "city": "Scottsdale",
    "state": "AZ",
    "query": "Scottsdale, AZ, USA",
    "coordinates": [
      -111.926018,
      33.4942189
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Scottsdale"
  },
  {
    "name": "WSI Tucson",
    "city": "Tucson",
    "state": "AZ",
    "query": "Tucson, AZ, USA",
    "coordinates": [
      -110.974847,
      32.2228765
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Tucson"
  },
  {
    "name": "WSI Rogers",
    "city": "Rogers",
    "state": "AR",
    "query": "Rogers, AR, USA",
    "coordinates": [
      -94.1193816,
      36.334857
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Rogers"
  },
  {
    "name": "WSI Corte Madera",
    "city": "Corte Madera",
    "state": "CA",
    "query": "Corte Madera, CA, USA",
    "coordinates": [
      -122.527475,
      37.9254806
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Corte Madera"
  },
  {
    "name": "WSI Costa Mesa",
    "city": "Costa Mesa",
    "state": "CA",
    "query": "Costa Mesa, CA, USA",
    "coordinates": [
      -117.903317,
      33.6633386
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Costa Mesa"
  },
  {
    "name": "WSI Fresno",
    "city": "Fresno",
    "state": "CA",
    "query": "Fresno, CA, USA",
    "coordinates": [
      -119.78483,
      36.7394421
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Fresno"
  },
  {
    "name": "WSI Los Angeles",
    "city": "Los Angeles",
    "state": "CA",
    "query": "Los Angeles, CA, USA",
    "coordinates": [
      -118.242766,
      34.0536909
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Los Angeles"
  },
  {
    "name": "WSI Manhattan Beach",
    "city": "Manhattan Beach",
    "state": "CA",
    "query": "Manhattan Beach, CA, USA",
    "coordinates": [
      -118.4104324,
      33.8872777
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Manhattan Beach"
  },
  {
    "name": "WSI Mission Viejo",
    "city": "Mission Viejo",
    "state": "CA",
    "query": "Mission Viejo, CA, USA",
    "coordinates": [
      -117.659405,
      33.5965685
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Mission Viejo"
  },
  {
    "name": "WSI Monterey",
    "city": "Monterey",
    "state": "CA",
    "query": "Monterey, CA, USA",
    "coordinates": [
      -121.387742,
      36.2231079
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Monterey"
  },
  {
    "name": "WSI Newport Coast",
    "city": "Newport Coast",
    "state": "CA",
    "query": "Newport Coast, CA, USA",
    "coordinates": [
      -117.826821,
      33.5963719
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Newport Coast"
  },
  {
    "name": "WSI Palm Desert",
    "city": "Palm Desert",
    "state": "CA",
    "query": "Palm Desert, CA, USA",
    "coordinates": [
      -116.382571,
      33.7288179
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Palm Desert"
  },
  {
    "name": "WSI Palo Alto",
    "city": "Palo Alto",
    "state": "CA",
    "query": "Palo Alto, CA, USA",
    "coordinates": [
      -122.1598465,
      37.4443293
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Palo Alto"
  },
  {
    "name": "WSI Pasadena",
    "city": "Pasadena",
    "state": "CA",
    "query": "Pasadena, CA, USA",
    "coordinates": [
      -118.144155,
      34.1476507
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Pasadena"
  },
  {
    "name": "WSI Rancho Cucamonga",
    "city": "Rancho Cucamonga",
    "state": "CA",
    "query": "Rancho Cucamonga, CA, USA",
    "coordinates": [
      -117.575173,
      34.1033192
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Rancho Cucamonga"
  },
  {
    "name": "WSI Roseville",
    "city": "Roseville",
    "state": "CA",
    "query": "Roseville, CA, USA",
    "coordinates": [
      -121.2880059,
      38.7521235
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Roseville"
  },
  {
    "name": "WSI Sacramento",
    "city": "Sacramento",
    "state": "CA",
    "query": "Sacramento, CA, USA",
    "coordinates": [
      -121.493895,
      38.5810606
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Sacramento"
  },
  {
    "name": "WSI San Diego",
    "city": "San Diego",
    "state": "CA",
    "query": "San Diego, CA, USA",
    "coordinates": [
      -117.162772,
      32.7174202
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI San Diego"
  },
  {
    "name": "WSI San Luis Obispo",
    "city": "San Luis Obispo",
    "state": "CA",
    "query": "San Luis Obispo, CA, USA",
    "coordinates": [
      -120.375716,
      35.3540209
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI San Luis Obispo"
  },
  {
    "name": "WSI San Mateo",
    "city": "San Mateo",
    "state": "CA",
    "query": "San Mateo, CA, USA",
    "coordinates": [
      -122.3330573,
      37.496904
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI San Mateo"
  },
  {
    "name": "WSI San Ramon",
    "city": "San Ramon",
    "state": "CA",
    "query": "San Ramon, CA, USA",
    "coordinates": [
      -121.9544387,
      37.7648021
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI San Ramon"
  },
  {
    "name": "WSI Santa Barbara",
    "city": "Santa Barbara",
    "state": "CA",
    "query": "Santa Barbara, CA, USA",
    "coordinates": [
      -119.702667,
      34.4221319
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Santa Barbara"
  },
  {
    "name": "WSI Santa Clara",
    "city": "Santa Clara",
    "state": "CA",
    "query": "Santa Clara, CA, USA",
    "coordinates": [
      -121.955174,
      37.3541132
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Santa Clara"
  },
  {
    "name": "WSI Santa Monica",
    "city": "Santa Monica",
    "state": "CA",
    "query": "Santa Monica, CA, USA",
    "coordinates": [
      -118.491227,
      34.0194704
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Santa Monica"
  },
  {
    "name": "WSI Sonoma",
    "city": "Sonoma",
    "state": "CA",
    "query": "Sonoma, CA, USA",
    "coordinates": [
      -122.8473388,
      38.5110803
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Sonoma"
  },
  {
    "name": "WSI Vacaville",
    "city": "Vacaville",
    "state": "CA",
    "query": "Vacaville, CA, USA",
    "coordinates": [
      -121.9877444,
      38.3565773
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Vacaville"
  },
  {
    "name": "WSI Walnut Creek",
    "city": "Walnut Creek",
    "state": "CA",
    "query": "Walnut Creek, CA, USA",
    "coordinates": [
      -122.0618702,
      37.9020731
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Walnut Creek"
  },
  {
    "name": "WSI Westlake Village",
    "city": "Westlake Village",
    "state": "CA",
    "query": "Westlake Village, CA, USA",
    "coordinates": [
      -118.8061794,
      34.1460234
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Westlake Village"
  },
  {
    "name": "WSI Broomfield",
    "city": "Broomfield",
    "state": "CO",
    "query": "Broomfield, CO, USA",
    "coordinates": [
      -105.05208,
      39.9403995
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Broomfield"
  },
  {
    "name": "WSI Colorado Springs",
    "city": "Colorado Springs",
    "state": "CO",
    "query": "Colorado Springs, CO, USA",
    "coordinates": [
      -104.825348,
      38.8339578
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Colorado Springs"
  },
  {
    "name": "WSI Denver",
    "city": "Denver",
    "state": "CO",
    "query": "Denver, CO, USA",
    "coordinates": [
      -104.984862,
      39.7392364
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Denver"
  },
  {
    "name": "WSI Littleton",
    "city": "Littleton",
    "state": "CO",
    "query": "Littleton, CO, USA",
    "coordinates": [
      -105.016649,
      39.613321
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Littleton"
  },
  {
    "name": "WSI Danbury",
    "city": "Danbury",
    "state": "CT",
    "query": "Danbury, CT, USA",
    "coordinates": [
      -73.4540111,
      41.394817
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Danbury"
  },
  {
    "name": "WSI South Windsor",
    "city": "South Windsor",
    "state": "CT",
    "query": "South Windsor, CT, USA",
    "coordinates": [
      -72.5562712,
      41.8352395
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI South Windsor"
  },
  {
    "name": "WSI Westport",
    "city": "Westport",
    "state": "CT",
    "query": "Westport, CT, USA",
    "coordinates": [
      -73.3578955,
      41.1414855
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Westport"
  },
  {
    "name": "WSI Boca Raton",
    "city": "Boca Raton",
    "state": "FL",
    "query": "Boca Raton, FL, USA",
    "coordinates": [
      -80.0830984,
      26.3586885
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Boca Raton"
  },
  {
    "name": "WSI Coral Gables",
    "city": "Coral Gables",
    "state": "FL",
    "query": "Coral Gables, FL, USA",
    "coordinates": [
      -80.2585107,
      25.7331105
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Coral Gables"
  },
  {
    "name": "WSI Hallandale Beach",
    "city": "Hallandale Beach",
    "state": "FL",
    "query": "Hallandale Beach, FL, USA",
    "coordinates": [
      -80.148379,
      25.9812025
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Hallandale Beach"
  },
  {
    "name": "WSI Miami",
    "city": "Miami",
    "state": "FL",
    "query": "Miami, FL, USA",
    "coordinates": [
      -80.1935973,
      25.7741566
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Miami"
  },
  {
    "name": "WSI Miramar Beach",
    "city": "Miramar Beach",
    "state": "FL",
    "query": "Miramar Beach, FL, USA",
    "coordinates": [
      -86.3616979,
      30.377985
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Miramar Beach"
  },
  {
    "name": "WSI Naples",
    "city": "Naples",
    "state": "FL",
    "query": "Naples, FL, USA",
    "coordinates": [
      -81.7942944,
      26.1421976
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Naples"
  },
  {
    "name": "WSI Palm Beach Gardens",
    "city": "Palm Beach Gardens",
    "state": "FL",
    "query": "Palm Beach Gardens, FL, USA",
    "coordinates": [
      -80.1386547,
      26.8233946
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Palm Beach Gardens"
  },
  {
    "name": "WSI Sarasota",
    "city": "Sarasota",
    "state": "FL",
    "query": "Sarasota, FL, USA",
    "coordinates": [
      -82.5308545,
      27.3365805
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Sarasota"
  },
  {
    "name": "WSI Tampa",
    "city": "Tampa",
    "state": "FL",
    "query": "Tampa, FL, USA",
    "coordinates": [
      -82.4583107,
      27.9449854
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Tampa"
  },
  {
    "name": "WSI Winter Park",
    "city": "Winter Park",
    "state": "FL",
    "query": "Winter Park, FL, USA",
    "coordinates": [
      -81.3510264,
      28.5977707
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Winter Park"
  },
  {
    "name": "WSI Alpharetta",
    "city": "Alpharetta",
    "state": "GA",
    "query": "Alpharetta, GA, USA",
    "coordinates": [
      -84.2945964,
      34.0755962
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Alpharetta"
  },
  {
    "name": "WSI Atlanta",
    "city": "Atlanta",
    "state": "GA",
    "query": "Atlanta, GA, USA",
    "coordinates": [
      -84.3898151,
      33.7544657
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Atlanta"
  },
  {
    "name": "WSI Dawsonville",
    "city": "Dawsonville",
    "state": "GA",
    "query": "Dawsonville, GA, USA",
    "coordinates": [
      -84.1190804,
      34.4212053
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Dawsonville"
  },
  {
    "name": "WSI Marietta",
    "city": "Marietta",
    "state": "GA",
    "query": "Marietta, GA, USA",
    "coordinates": [
      -84.5496148,
      33.9528472
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Marietta"
  },
  {
    "name": "WSI Boise",
    "city": "Boise",
    "state": "ID",
    "query": "Boise, ID, USA",
    "coordinates": [
      -116.200886,
      43.6166163
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Boise"
  },
  {
    "name": "WSI Chicago",
    "city": "Chicago",
    "state": "IL",
    "query": "Chicago, IL, USA",
    "coordinates": [
      -87.6244212,
      41.8755616
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Chicago"
  },
  {
    "name": "WSI Deer Park",
    "city": "Deer Park",
    "state": "IL",
    "query": "Deer Park, IL, USA",
    "coordinates": [
      -88.0814651,
      42.1608585
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Deer Park"
  },
  {
    "name": "WSI Geneva",
    "city": "Geneva",
    "state": "IL",
    "query": "Geneva, IL, USA",
    "coordinates": [
      -88.3053525,
      41.8875281
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Geneva"
  },
  {
    "name": "WSI Lake Forest",
    "city": "Lake Forest",
    "state": "IL",
    "query": "Lake Forest, IL, USA",
    "coordinates": [
      -87.8407055,
      42.2586461
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Lake Forest"
  },
  {
    "name": "WSI Oak Brook",
    "city": "Oak Brook",
    "state": "IL",
    "query": "Oak Brook, IL, USA",
    "coordinates": [
      -87.9289504,
      41.8328085
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Oak Brook"
  },
  {
    "name": "WSI INDIANAPOLIS",
    "city": "INDIANAPOLIS",
    "state": "IN",
    "query": "INDIANAPOLIS, IN, USA",
    "coordinates": [
      -86.1583502,
      39.7683331
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI INDIANAPOLIS"
  },
  {
    "name": "WSI West Des Moines",
    "city": "West Des Moines",
    "state": "IA",
    "query": "West Des Moines, IA, USA",
    "coordinates": [
      -93.7594059,
      41.5644476
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI West Des Moines"
  },
  {
    "name": "WSI Leawood",
    "city": "Leawood",
    "state": "KS",
    "query": "Leawood, KS, USA",
    "coordinates": [
      -94.6169012,
      38.966673
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Leawood"
  },
  {
    "name": "WSI Lexington",
    "city": "Lexington",
    "state": "KY",
    "query": "Lexington, KY, USA",
    "coordinates": [
      -84.4970393,
      38.0464066
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Lexington"
  },
  {
    "name": "WSI Louisville",
    "city": "Louisville",
    "state": "KY",
    "query": "Louisville, KY, USA",
    "coordinates": [
      -85.759407,
      38.2542376
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Louisville"
  },
  {
    "name": "WSI Annapolis",
    "city": "Annapolis",
    "state": "MD",
    "query": "Annapolis, MD, USA",
    "coordinates": [
      -76.492786,
      38.9786401
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Annapolis"
  },
  {
    "name": "WSI Baltimore",
    "city": "Baltimore",
    "state": "MD",
    "query": "Baltimore, MD, USA",
    "coordinates": [
      -76.610759,
      39.2908816
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Baltimore"
  },
  {
    "name": "WSI Bethesda",
    "city": "Bethesda",
    "state": "MD",
    "query": "Bethesda, MD, USA",
    "coordinates": [
      -77.1233587,
      38.9812726
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Bethesda"
  },
  {
    "name": "WSI Dedham",
    "city": "Dedham",
    "state": "MA",
    "query": "Dedham, MA, USA",
    "coordinates": [
      -71.1755732,
      42.2489143
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Dedham"
  },
  {
    "name": "WSI Hingham",
    "city": "Hingham",
    "state": "MA",
    "query": "Hingham, MA, USA",
    "coordinates": [
      -70.8897676,
      42.2417669
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Hingham"
  },
  {
    "name": "WSI Lynnfield",
    "city": "Lynnfield",
    "state": "MA",
    "query": "Lynnfield, MA, USA",
    "coordinates": [
      -71.0481084,
      42.5389836
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Lynnfield"
  },
  {
    "name": "WSI Mashpee",
    "city": "Mashpee",
    "state": "MA",
    "query": "Mashpee, MA, USA",
    "coordinates": [
      -70.4811383,
      41.6484421
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Mashpee"
  },
  {
    "name": "WSI Grand Rapids",
    "city": "Grand Rapids",
    "state": "MI",
    "query": "Grand Rapids, MI, USA",
    "coordinates": [
      -85.6678639,
      42.9632425
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Grand Rapids"
  },
  {
    "name": "WSI Lansing",
    "city": "Lansing",
    "state": "MI",
    "query": "Lansing, MI, USA",
    "coordinates": [
      -84.5546295,
      42.7338254
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Lansing"
  },
  {
    "name": "WSI Novi",
    "city": "Novi",
    "state": "MI",
    "query": "Novi, MI, USA",
    "coordinates": [
      -83.4754913,
      42.48059
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Novi"
  },
  {
    "name": "WSI Rochester Hills",
    "city": "Rochester Hills",
    "state": "MI",
    "query": "Rochester Hills, MI, USA",
    "coordinates": [
      -83.1499322,
      42.6583661
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Rochester Hills"
  },
  {
    "name": "WSI Troy",
    "city": "Troy",
    "state": "MI",
    "query": "Troy, MI, USA",
    "coordinates": [
      -83.1499304,
      42.6055893
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Troy"
  },
  {
    "name": "WSI Edina",
    "city": "Edina",
    "state": "MN",
    "query": "Edina, MN, USA",
    "coordinates": [
      -93.3501222,
      44.8897027
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Edina"
  },
  {
    "name": "WSI Minnetonka",
    "city": "Minnetonka",
    "state": "MN",
    "query": "Minnetonka, MN, USA",
    "coordinates": [
      -93.4638936,
      44.9405086
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Minnetonka"
  },
  {
    "name": "WSI Roseville",
    "city": "Roseville",
    "state": "MN",
    "query": "Roseville, MN, USA",
    "coordinates": [
      -93.1566107,
      45.0060767
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Roseville"
  },
  {
    "name": "WSI St. Louis",
    "city": "St. Louis",
    "state": "MO",
    "query": "St. Louis, MO, USA",
    "coordinates": [
      -90.190009,
      38.6254063
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI St. Louis"
  },
  {
    "name": "WSI Omaha",
    "city": "Omaha",
    "state": "NE",
    "query": "Omaha, NE, USA",
    "coordinates": [
      -95.9383758,
      41.2587459
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Omaha"
  },
  {
    "name": "WSI Henderson",
    "city": "Henderson",
    "state": "NV",
    "query": "Henderson, NV, USA",
    "coordinates": [
      -114.9822716,
      36.0319602
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Henderson"
  },
  {
    "name": "WSI Las Vegas",
    "city": "Las Vegas",
    "state": "NV",
    "query": "Las Vegas, NV, USA",
    "coordinates": [
      -115.1484131,
      36.1674263
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Las Vegas"
  },
  {
    "name": "WSI Reno",
    "city": "Reno",
    "state": "NV",
    "query": "Reno, NV, USA",
    "coordinates": [
      -119.812658,
      39.5261788
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Reno"
  },
  {
    "name": "WSI Salem",
    "city": "Salem",
    "state": "NH",
    "query": "Salem, NH, USA",
    "coordinates": [
      -71.2009035,
      42.7884957
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Salem"
  },
  {
    "name": "WSI Bridgewater",
    "city": "Bridgewater",
    "state": "NJ",
    "query": "Bridgewater, NJ, USA",
    "coordinates": [
      -74.5517146,
      40.5598127
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Bridgewater"
  },
  {
    "name": "WSI Hackensack",
    "city": "Hackensack",
    "state": "NJ",
    "query": "Hackensack, NJ, USA",
    "coordinates": [
      -74.0410667,
      40.8870781
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Hackensack"
  },
  {
    "name": "WSI Montclair",
    "city": "Montclair",
    "state": "NJ",
    "query": "Montclair, NJ, USA",
    "coordinates": [
      -74.2210643,
      40.8164458
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Montclair"
  },
  {
    "name": "WSI Montvale",
    "city": "Montvale",
    "state": "NJ",
    "query": "Montvale, NJ, USA",
    "coordinates": [
      -74.0229173,
      41.0467635
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Montvale"
  },
  {
    "name": "WSI North Brunswick",
    "city": "North Brunswick",
    "state": "NJ",
    "query": "North Brunswick, NJ, USA",
    "coordinates": [
      -74.476545,
      40.4539249
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI North Brunswick"
  },
  {
    "name": "WSI Princeton",
    "city": "Princeton",
    "state": "NJ",
    "query": "Princeton, NJ, USA",
    "coordinates": [
      -74.6597376,
      40.3496953
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Princeton"
  },
  {
    "name": "WSI Short Hills",
    "city": "Short Hills",
    "state": "NJ",
    "query": "Short Hills, NJ, USA",
    "coordinates": [
      -74.3377392,
      40.7381585
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Short Hills"
  },
  {
    "name": "WSI Shrewsbury",
    "city": "Shrewsbury",
    "state": "NJ",
    "query": "Shrewsbury, NJ, USA",
    "coordinates": [
      -74.0615285,
      40.3295547
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Shrewsbury"
  },
  {
    "name": "WSI Albuquerque",
    "city": "Albuquerque",
    "state": "NM",
    "query": "Albuquerque, NM, USA",
    "coordinates": [
      -106.650985,
      35.0841034
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Albuquerque"
  },
  {
    "name": "WSI Bridgehampton",
    "city": "Bridgehampton",
    "state": "NY",
    "query": "Bridgehampton, NY, USA",
    "coordinates": [
      -72.3103724,
      40.9312839
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Bridgehampton"
  },
  {
    "name": "WSI Garden City",
    "city": "Garden City",
    "state": "NY",
    "query": "Garden City, NY, USA",
    "coordinates": [
      -73.6343052,
      40.7266477
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Garden City"
  },
  {
    "name": "WSI Huntington Station",
    "city": "Huntington Station",
    "state": "NY",
    "query": "Huntington Station, NY, USA",
    "coordinates": [
      -73.4036319,
      40.8472369
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Huntington Station"
  },
  {
    "name": "WSI New York",
    "city": "New York",
    "state": "NY",
    "query": "New York, NY, USA",
    "coordinates": [
      -74.0060152,
      40.7127281
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI New York"
  },
  {
    "name": "WSI Riverhead",
    "city": "Riverhead",
    "state": "NY",
    "query": "Riverhead, NY, USA",
    "coordinates": [
      -72.6624189,
      40.9168692
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Riverhead"
  },
  {
    "name": "WSI Victor",
    "city": "Victor",
    "state": "NY",
    "query": "Victor, NY, USA",
    "coordinates": [
      -77.4088794,
      42.9825634
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Victor"
  },
  {
    "name": "WSI White Plains",
    "city": "White Plains",
    "state": "NY",
    "query": "White Plains, NY, USA",
    "coordinates": [
      -73.7629097,
      41.0339862
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI White Plains"
  },
  {
    "name": "WSI Asheville",
    "city": "Asheville",
    "state": "NC",
    "query": "Asheville, NC, USA",
    "coordinates": [
      -82.5508407,
      35.595363
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Asheville"
  },
  {
    "name": "WSI Cary",
    "city": "Cary",
    "state": "NC",
    "query": "Cary, NC, USA",
    "coordinates": [
      -78.7812081,
      35.7882893
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Cary"
  },
  {
    "name": "WSI Charlotte",
    "city": "Charlotte",
    "state": "NC",
    "query": "Charlotte, NC, USA",
    "coordinates": [
      -80.8430827,
      35.2272086
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Charlotte"
  },
  {
    "name": "WSI Durham",
    "city": "Durham",
    "state": "NC",
    "query": "Durham, NC, USA",
    "coordinates": [
      -78.9018053,
      35.996653
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Durham"
  },
  {
    "name": "WSI Greensboro",
    "city": "Greensboro",
    "state": "NC",
    "query": "Greensboro, NC, USA",
    "coordinates": [
      -79.7919754,
      36.0726355
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Greensboro"
  },
  {
    "name": "WSI Huntersville",
    "city": "Huntersville",
    "state": "NC",
    "query": "Huntersville, NC, USA",
    "coordinates": [
      -80.8429304,
      35.4108278
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Huntersville"
  },
  {
    "name": "WSI Wilmington",
    "city": "Wilmington",
    "state": "NC",
    "query": "Wilmington, NC, USA",
    "coordinates": [
      -77.9487284,
      34.2352853
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Wilmington"
  },
  {
    "name": "WSI Beachwood",
    "city": "Beachwood",
    "state": "OH",
    "query": "Beachwood, OH, USA",
    "coordinates": [
      -81.508732,
      41.464498
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Beachwood"
  },
  {
    "name": "WSI Cincinnati",
    "city": "Cincinnati",
    "state": "OH",
    "query": "Cincinnati, OH, USA",
    "coordinates": [
      -84.5124602,
      39.1014537
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Cincinnati"
  },
  {
    "name": "WSI Columbus",
    "city": "Columbus",
    "state": "OH",
    "query": "Columbus, OH, USA",
    "coordinates": [
      -83.0007065,
      39.9622601
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Columbus"
  },
  {
    "name": "WSI Oklahoma City",
    "city": "Oklahoma City",
    "state": "OK",
    "query": "Oklahoma City, OK, USA",
    "coordinates": [
      -97.5170536,
      35.4729886
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Oklahoma City"
  },
  {
    "name": "WSI Tulsa",
    "city": "Tulsa",
    "state": "OK",
    "query": "Tulsa, OK, USA",
    "coordinates": [
      -95.9927516,
      36.1563122
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Tulsa"
  },
  {
    "name": "WSI Portland",
    "city": "Portland",
    "state": "OR",
    "query": "Portland, OR, USA",
    "coordinates": [
      -122.674194,
      45.5202471
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Portland"
  },
  {
    "name": "WSI Tigard",
    "city": "Tigard",
    "state": "OR",
    "query": "Tigard, OR, USA",
    "coordinates": [
      -122.771933,
      45.4307473
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Tigard"
  },
  {
    "name": "WSI Glen Mills",
    "city": "Glen Mills",
    "state": "PA",
    "query": "Glen Mills, PA, USA",
    "coordinates": [
      -75.4904323,
      39.919698
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Glen Mills"
  },
  {
    "name": "WSI Harrisburg",
    "city": "Harrisburg",
    "state": "PA",
    "query": "Harrisburg, PA, USA",
    "coordinates": [
      -76.8861122,
      40.2663107
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Harrisburg"
  },
  {
    "name": "WSI King of Prussia",
    "city": "King of Prussia",
    "state": "PA",
    "query": "King of Prussia, PA, USA",
    "coordinates": [
      -75.3851334,
      40.0947625
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI King of Prussia"
  },
  {
    "name": "WSI Pittsburgh",
    "city": "Pittsburgh",
    "state": "PA",
    "query": "Pittsburgh, PA, USA",
    "coordinates": [
      -80.0025666,
      40.4406968
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Pittsburgh"
  },
  {
    "name": "WSI San Juan",
    "city": "San Juan",
    "state": "PR",
    "query": "San Juan, PR, USA",
    "coordinates": [
      -66.116666,
      18.465299
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI San Juan"
  },
  {
    "name": "WSI Cranston",
    "city": "Cranston",
    "state": "RI",
    "query": "Cranston, RI, USA",
    "coordinates": [
      -71.4366813,
      41.779588
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Cranston"
  },
  {
    "name": "WSI Charleston",
    "city": "Charleston",
    "state": "SC",
    "query": "Charleston, SC, USA",
    "coordinates": [
      -79.9399309,
      32.7884363
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Charleston"
  },
  {
    "name": "WSI Franklin",
    "city": "Franklin",
    "state": "TN",
    "query": "Franklin, TN, USA",
    "coordinates": [
      -86.8689419,
      35.925206
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Franklin"
  },
  {
    "name": "WSI Knoxville",
    "city": "Knoxville",
    "state": "TN",
    "query": "Knoxville, TN, USA",
    "coordinates": [
      -83.9210261,
      35.9603948
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Knoxville"
  },
  {
    "name": "WSI Nashville",
    "city": "Nashville",
    "state": "TN",
    "query": "Nashville, TN, USA",
    "coordinates": [
      -86.7742984,
      36.1622767
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Nashville"
  },
  {
    "name": "WSI Austin",
    "city": "Austin",
    "state": "TX",
    "query": "Austin, TX, USA",
    "coordinates": [
      -97.7436995,
      30.2711286
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Austin"
  },
  {
    "name": "WSI Dallas",
    "city": "Dallas",
    "state": "TX",
    "query": "Dallas, TX, USA",
    "coordinates": [
      -96.7968559,
      32.7762719
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Dallas"
  },
  {
    "name": "WSI Fort Worth",
    "city": "Fort Worth",
    "state": "TX",
    "query": "Fort Worth, TX, USA",
    "coordinates": [
      -97.3327459,
      32.753177
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Fort Worth"
  },
  {
    "name": "WSI Houston",
    "city": "Houston",
    "state": "TX",
    "query": "Houston, TX, USA",
    "coordinates": [
      -95.3676974,
      29.7589382
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Houston"
  },
  {
    "name": "WSI Plano",
    "city": "Plano",
    "state": "TX",
    "query": "Plano, TX, USA",
    "coordinates": [
      -96.6925096,
      33.0136764
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Plano"
  },
  {
    "name": "WSI San Antonio",
    "city": "San Antonio",
    "state": "TX",
    "query": "San Antonio, TX, USA",
    "coordinates": [
      -98.4951405,
      29.4246002
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI San Antonio"
  },
  {
    "name": "WSI Southlake",
    "city": "Southlake",
    "state": "TX",
    "query": "Southlake, TX, USA",
    "coordinates": [
      -97.1341783,
      32.9412363
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Southlake"
  },
  {
    "name": "WSI Salt Lake City",
    "city": "Salt Lake City",
    "state": "UT",
    "query": "Salt Lake City, UT, USA",
    "coordinates": [
      -111.886797,
      40.7596198
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Salt Lake City"
  },
  {
    "name": "WSI Arlington",
    "city": "Arlington",
    "state": "VA",
    "query": "Arlington, VA, USA",
    "coordinates": [
      -77.0893094,
      38.8769326
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Arlington"
  },
  {
    "name": "WSI Fairfax",
    "city": "Fairfax",
    "state": "VA",
    "query": "Fairfax, VA, USA",
    "coordinates": [
      -77.3063733,
      38.8462236
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Fairfax"
  },
  {
    "name": "WSI Leesburg",
    "city": "Leesburg",
    "state": "VA",
    "query": "Leesburg, VA, USA",
    "coordinates": [
      -77.5645607,
      39.1154506
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Leesburg"
  },
  {
    "name": "WSI Richmond",
    "city": "Richmond",
    "state": "VA",
    "query": "Richmond, VA, USA",
    "coordinates": [
      -77.43428,
      37.5385087
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Richmond"
  },
  {
    "name": "WSI Virginia Beach",
    "city": "Virginia Beach",
    "state": "VA",
    "query": "Virginia Beach, VA, USA",
    "coordinates": [
      -75.9760751,
      36.8496579
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Virginia Beach"
  },
  {
    "name": "WSI Bellevue",
    "city": "Bellevue",
    "state": "WA",
    "query": "Bellevue, WA, USA",
    "coordinates": [
      -122.192337,
      47.6144219
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Bellevue"
  },
  {
    "name": "WSI Seattle",
    "city": "Seattle",
    "state": "WA",
    "query": "Seattle, WA, USA",
    "coordinates": [
      -122.330062,
      47.6038321
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Seattle"
  },
  {
    "name": "WSI Spokane",
    "city": "Spokane",
    "state": "WA",
    "query": "Spokane, WA, USA",
    "coordinates": [
      -117.42351,
      47.6571934
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Spokane"
  },
  {
    "name": "WSI Wauwatosa",
    "city": "Wauwatosa",
    "state": "WI",
    "query": "Wauwatosa, WI, USA",
    "coordinates": [
      -88.0079271,
      43.0494122
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Wauwatosa"
  },
  {
    "name": "WSI Calgary",
    "city": "Calgary",
    "state": "AB",
    "query": "Calgary, AB, USA",
    "coordinates": [
      -94.1193622,
      31.6174004
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Calgary"
  },
  {
    "name": "WSI Vancouver",
    "city": "Vancouver",
    "state": "BC",
    "query": "Vancouver, BC, USA",
    "coordinates": [
      -122.6744557,
      45.6306954
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI Vancouver"
  },
  {
    "name": "WSI North York",
    "city": "North York",
    "state": "ON",
    "query": "North York, ON, USA",
    "coordinates": [
      -87.5443721,
      38.0299665
    ],
    "type": "STORE",
    "status": "Operational",
    "suppliedBy": "Regional Hub",
    "id": "WSI North York"
  }
];
