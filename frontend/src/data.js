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
