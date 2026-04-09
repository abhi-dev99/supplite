import { useState } from 'react';
import DeckGL from '@deck.gl/react';
import { ColumnLayer, GeoJsonLayer, ScatterplotLayer } from '@deck.gl/layers';
import { geoClusters, storeLocations } from '../data';

// Using a lightweight public GeoJSON of US states for the base map
const US_STATES_URL = 'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json';

const INITIAL_VIEW_STATE = {
  longitude: -98.0,
  latitude: 38.0,
  zoom: 3.5,
  maxZoom: 16,
  pitch: 50,
  bearing: -10
};

export default function SciFiMap({ isFullscreen = false }) {
  const [hoverInfo, setHoverInfo] = useState(null);
  const [storeHover, setStoreHover] = useState(null);
  
  const layers = [
    // The Base Map (Wireframe Sci-Fi Aesthetic)
    new GeoJsonLayer({
      id: 'us-states-layer',
      data: US_STATES_URL,
      filled: true,
      stroked: true,
      lineWidthMinPixels: 1,
      getLineColor: [0, 150, 255, 60],
      getFillColor: [10, 15, 25, 200], // Very dark deep blue/black
      pickable: false
    }),

    // WSI Retail Store Locations
    new ScatterplotLayer({
      id: 'retail-stores-layer',
      data: storeLocations,
      pickable: true,
      opacity: 0.8,
      stroked: true,
      filled: true,
      radiusScale: 1,
      radiusMinPixels: 3,
      radiusMaxPixels: 10,
      lineWidthMinPixels: 1,
      getPosition: d => d.position,
      getFillColor: [255, 255, 255, 200], // Bright white dots for stores
      getLineColor: [0, 150, 255, 255],
      onHover: info => setStoreHover(info)
    }),

    // The Risk Severity Pillars
    new ColumnLayer({
      id: 'column-layer',
      data: geoClusters,
      diskResolution: 6,
      radius: 12000,
      extruded: true,
      pickable: true,
      elevationScale: 60,
      getPosition: d => d.position,
      getFillColor: d => {
        if (d.risk === 'STOCKOUT_RISK') return [255, 60, 60, 220]; // Red
        if (d.risk === 'OVERSTOCK_RISK') return [255, 180, 40, 220]; // Amber
        return [40, 160, 255, 220]; // Blue
      },
      getElevation: d => d.volume,
      onHover: info => setHoverInfo(info)
    })
  ];

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', backgroundColor: '#020202', borderRadius: isFullscreen ? '0' : '8px', overflow: 'hidden' }}>
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={layers}
      />
      
      {/* Store Tooltip */}
      {storeHover && storeHover.object && !hoverInfo?.object && (
        <div style={{
          position: 'absolute', zIndex: 2, pointerEvents: 'none', left: storeHover.x, top: storeHover.y,
          backgroundColor: 'rgba(255, 255, 255, 0.95)', padding: '12px', color: '#000', borderRadius: '4px',
          boxShadow: '0 4px 16px rgba(0,0,0,0.5)', fontSize: '0.75rem', transform: 'translate(-50%, -120%)',
          fontWeight: 600
        }}>
          {storeHover.object.name}
          <div style={{ color: '#666', fontWeight: 400, marginTop: '4px' }}>WSI Retail Storefront</div>
        </div>
      )}

      {/* Risk Pillar Tooltip */}
      {hoverInfo && hoverInfo.object && (
        <div style={{
          position: 'absolute', zIndex: 2, pointerEvents: 'none', left: hoverInfo.x, top: hoverInfo.y,
          backgroundColor: 'rgba(5, 5, 10, 0.95)', padding: '16px', color: '#fff', borderRadius: '6px',
          border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 8px 32px rgba(0,0,0,0.8)',
          fontSize: '0.75rem', transform: 'translate(-50%, -120%)', width: '240px',
          fontFamily: 'var(--font-sans)', backdropFilter: 'blur(10px)'
        }}>
          <div style={{ fontWeight: 600, borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '12px', marginBottom: '12px', fontSize: '0.875rem' }}>
            Tactical Analysis: {hoverInfo.object.hub}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={{ color: 'rgba(255,255,255,0.5)' }}>ZIP Sector:</div>
            <div style={{ fontFamily: 'monospace' }}>{hoverInfo.object.zipPrefix}</div>
            
            <div style={{ color: 'rgba(255,255,255,0.5)' }}>Risk Class:</div>
            <div style={{ color: hoverInfo.object.risk === 'STOCKOUT_RISK' ? '#ff3c3c' : hoverInfo.object.risk === 'OVERSTOCK_RISK' ? '#ffb428' : '#28a0ff', fontWeight: 600 }}>
              {hoverInfo.object.risk.replace('_', ' ')}
            </div>
            
            <div style={{ color: 'rgba(255,255,255,0.5)' }}>Affected Volume:</div>
            <div>{hoverInfo.object.volume.toLocaleString()} Units</div>
            
            <div style={{ color: 'rgba(255,255,255,0.5)' }}>Forecast Delay:</div>
            <div>{hoverInfo.object.delay}</div>
          </div>
        </div>
      )}
      
      {/* Sci-Fi HUD Overlays */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, pointerEvents: 'none',
        background: 'radial-gradient(circle at center, transparent 30%, rgba(0, 0, 0, 0.4) 100%)',
        boxShadow: 'inset 0 0 100px rgba(0,0,0,0.9)', zIndex: 1
      }} />
    </div>
  );
}
