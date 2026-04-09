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

export const distributionCenters = [
  { name: 'City of Industry DC', coordinates: [-117.9654, 34.0200], region: 'West Coast', radiusMiles: 600, status: 'Active' },
  { name: 'Arlington DC', coordinates: [-97.1081, 32.7357], region: 'South Central', radiusMiles: 500, status: 'Active' },
  { name: 'Memphis DC', coordinates: [-90.0490, 35.1495], region: 'Mid-West', radiusMiles: 400, status: 'Active' },
  { name: 'Olive Branch DC', coordinates: [-89.8295, 34.9618], region: 'South', radiusMiles: 400, status: 'Active' },
  { name: 'Braselton DC', coordinates: [-83.7627, 34.1084], region: 'Southeast', radiusMiles: 350, status: 'Active' },
  { name: 'South Brunswick DC', coordinates: [-74.5204, 40.3846], region: 'Northeast', radiusMiles: 300, status: 'Active' }
];

export const wsStores = Array.from({ length: 180 }).map((_, i) => {
  // Tie each store to a specific distribution center territory
  const dc = distributionCenters[Math.floor(Math.random() * distributionCenters.length)];
  // 1 degree coordinates roughly = 69 miles. We spread them within the DC's operating radius.
  const spreadRadius = dc.radiusMiles / 69; 
  const offX = (Math.random() - 0.5) * spreadRadius * 1.5; 
  const offY = (Math.random() - 0.5) * spreadRadius;
  
  return {
    id: `WS-Node-${i}`,
    name: 'Williams Sonoma Hub',
    coordinates: [dc.coordinates[0] + offX, dc.coordinates[1] + offY],
    type: 'STORE',
    status: 'Operational',
    suppliedBy: dc.name
  };
});
