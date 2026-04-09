import { useState, useEffect } from 'react';
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps';

// Using a standard US map TopoJSON from jsdelivr
const geoUrl = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

export default function RiskHeatmap() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  // Hotspots representing port congestion / risk areas
  const markers = [
    { name: "LA Port", coordinates: [-118.24, 34.05], risk: "high" },
    { name: "NY Hub", coordinates: [-74.00, 40.71], risk: "high" },
    { name: "TX DC", coordinates: [-96.79, 32.77], risk: "medium" }
  ];

  if (!mounted) return null;

  return (
    <div style={{ width: '100%', height: '140px', position: 'relative' }}>
      <ComposableMap projection="geoAlbersUsa" projectionConfig={{ scale: 300 }} style={{ width: "100%", height: "100%" }}>
        <Geographies geography={geoUrl}>
          {({ geographies }) =>
            geographies.map(geo => (
              <Geography
                key={geo.rsmKey}
                geography={geo}
                fill="var(--color-surface-hover)"
                stroke="var(--color-surface-floating)"
                strokeWidth={0.5}
                style={{
                  default: { outline: 'none' },
                  hover: { fill: 'var(--color-surface)', outline: 'none' },
                  pressed: { outline: 'none' },
                }}
              />
            ))
          }
        </Geographies>
        {markers.map(({ name, coordinates, risk }) => (
          <Marker key={name} coordinates={coordinates}>
            <circle 
              r={risk === 'high' ? 6 : 4} 
              fill={risk === 'high' ? "var(--color-stockout-text)" : "var(--color-overstock-text)"}
              opacity={0.6}
            />
            <circle 
              r={risk === 'high' ? 2 : 1} 
              fill="white"
            />
          </Marker>
        ))}
      </ComposableMap>
    </div>
  );
}
