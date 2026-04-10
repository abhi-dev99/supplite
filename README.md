# Demand Intelligence System

A high-fidelity, interactive supply chain and retail analytics dashboard designed for enterprise resource oversight and predictive inventory modeling. The platform integrates true geospatial routing, nearest-neighbor algorithmic territorial boundaries, and full-stack interactive metrics mapping seamlessly into a customized graphical interface.

![Demand Intelligence Banner](https://img.shields.io/badge/Status-Active_Development-brightgreen)
![React](https://img.shields.io/badge/React-v18-blue)
![Deck.gl](https://img.shields.io/badge/Map-deck.gl-orange)
![Python](https://img.shields.io/badge/Scripts-Python3-yellow)

## 🚀 Key Features

*   **Interactive 3D Geospatial Grid:** Powered by `deck.gl` and `react-map-gl`, rendering active distribution territories, 3D signal columns representing stock vulnerabilities, and pinpoint mappings of hundreds of storefronts.
*   **Dynamic Territorial Processing:** A bespoke mathematical algorithm computes service territories for Distribution Centers precisely using Haversine nearest-neighbor mechanics, guaranteeing exact visualization of non-overlapping bounds across the real-world dataset.
*   **Smart HUD & Logic Filtering:** Toggle real-time logistics networks (Manufacturing, DCs, Storefronts) and risk metrics on the fly using the contextual map legend.
*   **Theming Options:** Deep dynamic environment mapping handling high-contrast layout configurations for strict Light Mode enterprise visibility or standard sci-fi Dark Mode aesthetics natively.
*   **Data Abstraction Pipeline:** Uses dedicated Node/Python hybrid scripts traversing native datasets and geocoding via OpenStreetMap Nominatim APIs offline so raw JSON configs drop natively into the React app.

## 📂 Project Architecture

```
/supplite
│── README.md
│── .gitignore
│── LICENSE
├── data/                       # Contains raw parsing datasets (Hubs, Territories, Stores list)
│   ├── supply chain items.txt
│   ├── wsi stores.txt
│   └── parsed_stores.json
├── update_infrastructure.py    # Python script parsing and geocoding supply chain nodes
├── parse_stores.py             # Python script geocoding full WSI retail fleets
├── replace_stores.py           # Bridging script to port JSON configs directly into frontend
└── frontend/                   # Main React Application
    ├── public/
    │   └── na_map.json         # North American boundary configurations
    ├── src/
    │   ├── components/         # Map instances, HUD components, Overlays
    │   ├── views/              # Pages (SkuRiskOverview, BuyerBrief, Simulation, etc)
    │   └── data.js             # The Single Source of Truth containing all dynamically rendered variables
    ├── index.css
    └── package.json
```

## 🛠️ Local Development Server

Getting started is extremely straightforward. 

### 1. Requirements
- Node.js (v18+)
- Python 3.9+ (if requiring dataset geocoding regeneration)
- Git

### 2. Quickstart

To run the primary client UI server locally, navigate to the `frontend/` directory, install dependencies via `npm`, and spin up the Vite development server.

```bash
# Clone the repository
git clone https://github.com/abhi-dev99/supplite.git
cd supplite

# Enter frontend environment
cd frontend
npm install

# Start development port (defaults to localhost:5173 or similar depending on free ports)
npm run dev
```

### 3. Re-generating Geospatial Datasets

If you modify the text documents in `/data/` to include new physical hub locations, new customer care nodes, or more retail locations, you must regenerate the static `data.js` dictionaries. Ensure you are in the root `supplite` directory.

Geocode and pipe the global supply chain:
```bash
python update_infrastructure.py
```

Geocode and pipe a new retail fleet dictionary:
```bash
python parse_stores.py
python C:\Users\abhi\.gemini\antigravity\brain\3a7d486f-acab-4266-a56a-f07784c353d8\scratch\territory_math.py
```

*(Note: The custom `territory_math.py` binds each store uniquely to the absolute closest DC mathematically—do not skip this step or your DC ranges will default!).*

## 📄 License

This project operates under the **MIT License**. Check the `LICENSE` file for exact distribution specifications.
