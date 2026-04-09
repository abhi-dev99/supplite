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

export const geoClusters = Array.from({ length: 2500 }).map(() => {
  // Center roughly around massive logistics hubs/metros
  const centers = [
     { name: 'LA Port Authority', lng: -118.24, lat: 34.05, weight: 4.5, type: 'STOCKOUT_RISK' },
     { name: 'Northeast Corridor', lng: -74.00, lat: 40.71, weight: 5.2, type: 'WATCH' },
     { name: 'Dallas DC', lng: -96.79, lat: 32.77, weight: 3.8, type: 'OVERSTOCK_RISK' },
     { name: 'Chicago Rail Hub', lng: -87.62, lat: 41.87, weight: 3.0, type: 'STOCKOUT_RISK' },
     { name: 'Seattle Port', lng: -122.33, lat: 47.60, weight: 2.0, type: 'WATCH' }
  ];
  const c = centers[Math.floor(Math.random() * centers.length)];
  
  // Create normally distributed spread
  const lngOff = (Math.random() - 0.5) * c.weight + (Math.random() - 0.5) * c.weight;
  const latOff = (Math.random() - 0.5) * (c.weight/1.5) + (Math.random() - 0.5) * (c.weight/1.5);
  
  return {
     hub: c.name,
     zipPrefix: String(Math.floor(Math.random() * 90000) + 10000),
     position: [c.lng + lngOff, c.lat + latOff],
     risk: c.type === 'STOCKOUT_RISK' ? 'STOCKOUT_RISK' : (Math.random() > 0.5 ? 'OVERSTOCK_RISK' : 'WATCH'),
     volume: Math.floor(Math.random() * 1200) + 50,
     delay: Math.floor(Math.random() * 14) + ' Days'
  };
});

export const storeLocations = [
  { name: "Williams Sonoma - Beverly Hills, CA", position: [-118.4004, 34.0736] },
  { name: "Pottery Barn - San Francisco, CA", position: [-122.4194, 37.7749] },
  { name: "West Elm - Austin, TX", position: [-97.7431, 30.2672] },
  { name: "Williams Sonoma - Chicago, IL", position: [-87.6298, 41.8781] },
  { name: "Pottery Barn - Miami, FL", position: [-80.1918, 25.7617] },
  { name: "West Elm - Brooklyn, NY", position: [-73.9442, 40.6782] },
  { name: "Williams Sonoma - Boston, MA", position: [-71.0589, 42.3601] },
  { name: "Pottery Barn - Seattle, WA", position: [-122.3321, 47.6062] },
  { name: "West Elm - Denver, CO", position: [-104.9903, 39.7392] },
  { name: "Williams Sonoma - Atlanta, GA", position: [-84.3880, 33.7490] }
];
