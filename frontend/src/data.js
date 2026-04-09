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

export const wsStores = [
  { name: 'Williams Sonoma Columbus Circle', coordinates: [-73.9822, 40.7681], type: 'STORE', status: 'Operational' },
  { name: 'Williams Sonoma Beverly Hills', coordinates: [-118.4021, 34.0689], type: 'STORE', status: 'Operational' },
  { name: 'Williams Sonoma Union Square SF', coordinates: [-122.4075, 37.7876], type: 'STORE', status: 'Operational' },
  { name: 'Williams Sonoma NorthPark Center Dallas', coordinates: [-96.7730, 32.8687], type: 'STORE', status: 'Operational' },
  { name: 'Williams Sonoma Lincoln Park Chicago', coordinates: [-87.6534, 41.9137], type: 'STORE', status: 'Operational' },
  { name: 'Williams Sonoma Lenox Square Atlanta', coordinates: [-84.3608, 33.8463], type: 'STORE', status: 'Operational' },
  { name: 'Williams Sonoma King of Prussia', coordinates: [-75.3888, 40.0894], type: 'STORE', status: 'Operational' },
  { name: 'Williams Sonoma Seattle U-Village', coordinates: [-122.2985, 47.6625], type: 'STORE', status: 'Operational' },
  { name: 'Williams Sonoma Coral Gables', coordinates: [-80.2600, 25.7335], type: 'STORE', status: 'Operational' },
  { name: 'Williams Sonoma Boston Copley Place', coordinates: [-71.0772, 42.3475], type: 'STORE', status: 'Operational' },
  { name: 'Williams Sonoma Denver Cherry Creek', coordinates: [-104.9536, 39.7169], type: 'STORE', status: 'Operational' },
  { name: 'Williams Sonoma Short Hills NJ', coordinates: [-74.3214, 40.7410], type: 'STORE', status: 'Operational' },
];
