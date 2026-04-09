import { useState } from 'react';
import DeckGL from '@deck.gl/react';
import { ColumnLayer, ScatterplotLayer, GeoJsonLayer } from '@deck.gl/layers';
import { geoClusters, wsStores } from '../data';

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
  
  const layers = [
    // The Base Map holding the US state geometry (Fixes the black void)
    new GeoJsonLayer({
      id: 'us-states-geometry',
      data: 'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json',
      stroked: true,
      filled: true,
      lineWidthMinPixels: 1,
      getLineColor: [30, 255, 255, 60], // Cyan glowing borders
      getFillColor: [10, 15, 25, 200], // Dark void terrain
    }),

    // The Williams-Sonoma Retail Store Instances
    new ScatterplotLayer({
      id: 'store-locations',
      data: wsStores,
      pickable: true,
      opacity: 1,
      stroked: true,
      filled: true,
      radiusScale: 5000,
      radiusMinPixels: 4,
      radiusMaxPixels: 12,
      lineWidthMinPixels: 1,
      getPosition: d => d.coordinates,
      getFillColor: [255, 255, 255, 255], // White center
      getLineColor: [0, 255, 255, 255], // Cyan outline
      onHover: info => setHoverInfo(info)
    }),

    // The Projected Risk Densities (3D Pillars)
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
      
      {/* Sci-Fi Tooltip HUD */}
      {hoverInfo && hoverInfo.object && (
        <div style={{
          position: 'absolute',
          zIndex: 1,
          pointerEvents: 'none',
          left: hoverInfo.x,
          top: hoverInfo.y,
          backgroundColor: 'rgba(5, 5, 10, 0.95)',
          padding: '16px',
          color: '#fff',
          borderRadius: '6px',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.8)',
          fontSize: '0.75rem',
          transform: 'translate(-50%, -120%)',
          width: '240px',
          fontFamily: 'var(--font-sans)',
          backdropFilter: 'blur(10px)'
        }}>
          {hoverInfo.object.type === 'STORE' ? (
             <>
               <div style={{ fontWeight: 600, borderBottom: '1px solid rgba(0,255,255,0.3)', paddingBottom: '12px', marginBottom: '12px', fontSize: '0.875rem', color: '#00ffff' }}>
                 WSI Retail Terminal
               </div>
               <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                 <div style={{ fontWeight: 600 }}>{hoverInfo.object.name}</div>
                 <div style={{ display: 'flex', justifyContent: 'space-between', color: 'rgba(255,255,255,0.5)' }}>
                    <span>Network Status:</span>
                    <span style={{ color: '#86efac', fontWeight: 600 }}>{hoverInfo.object.status}</span>
                 </div>
               </div>
             </>
          ) : (
             <>
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
             </>
          )}
        </div>
      )}
      
      {/* Sci-Fi HUD Overlays */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0, bottom: 0,
        pointerEvents: 'none',
        background: 'radial-gradient(circle at center, transparent 30%, rgba(0, 0, 0, 0.4) 100%)',
        boxShadow: 'inset 0 0 100px rgba(0,0,0,0.9)'
      }} />
    </div>
  );
}
