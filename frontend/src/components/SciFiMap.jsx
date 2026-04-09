import { useState } from 'react';
import DeckGL from '@deck.gl/react';
import { ColumnLayer, ScatterplotLayer, GeoJsonLayer } from '@deck.gl/layers';
import { geoClusters, wsStores, distributionCenters } from '../data';

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
  const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);
  
  const layers = [
    // 1. The Base Map holding the US state geometry
    new GeoJsonLayer({
      id: 'us-states-geometry',
      data: 'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json',
      stroked: true,
      filled: true,
      lineWidthMinPixels: 1,
      getLineColor: [30, 255, 255, 40], // Faint cyan borders
      getFillColor: [10, 15, 25, 200], // Dark void terrain
    }),

    // 2. The Service Territory Radars (Massive translucent circles around DCs)
    new ScatterplotLayer({
      id: 'dc-territory-rings',
      data: distributionCenters,
      pickable: false,
      opacity: 0.15,
      stroked: true,
      filled: true,
      radiusScale: 1609, // Convert miles to meters (approx)
      radiusMinPixels: 10,
      lineWidthMinPixels: 2,
      getPosition: d => d.coordinates,
      getRadius: d => d.radiusMiles, // This makes it massive
      getFillColor: [255, 60, 60], // Transparent red threat rings
      getLineColor: [255, 60, 60, 150], 
    }),

    // 3. The 6 Main Distribution Center Nodes (Bright large dots)
    new ScatterplotLayer({
      id: 'dc-nodes',
      data: distributionCenters,
      pickable: true,
      opacity: 1,
      stroked: true,
      filled: true,
      radiusScale: 8000,
      radiusMinPixels: 6,
      radiusMaxPixels: 15,
      lineWidthMinPixels: 2,
      getPosition: d => d.coordinates,
      getFillColor: [255, 255, 255], 
      getLineColor: [255, 60, 60], // Red ring
      onHover: info => setHoverInfo(info)
    }),

    // 4. The 180 Generated WSI Retail Storefronts
    new ScatterplotLayer({
      id: 'store-locations',
      data: wsStores,
      pickable: true,
      opacity: 0.9,
      stroked: false,
      filled: true,
      radiusScale: 3000,
      radiusMinPixels: 2,
      radiusMaxPixels: 6,
      getPosition: d => d.coordinates,
      getFillColor: [0, 255, 200, 255], // Sci-fi cyan nodes
      onHover: info => setHoverInfo(info)
    }),

    // 5. The Projected Risk Densities (3D Pillars from Demand Signal Data)
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
        viewState={viewState}
        onViewStateChange={({ viewState }) => setViewState(viewState)}
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
          width: '260px',
          fontFamily: 'var(--font-sans)',
          backdropFilter: 'blur(10px)'
        }}>
          {hoverInfo.layer.id === 'dc-nodes' ? (
             <>
               <div style={{ fontWeight: 600, borderBottom: '1px solid rgba(255,60,60,0.4)', paddingBottom: '12px', marginBottom: '12px', fontSize: '0.875rem', color: '#ff3c3c' }}>
                 WSI Distribution Center (HQ)
               </div>
               <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                 <div style={{ fontWeight: 600 }}>{hoverInfo.object.name}</div>
                 <div style={{ display: 'flex', justifyContent: 'space-between', color: 'rgba(255,255,255,0.5)' }}>
                    <span>Territory Radius:</span>
                    <span>{hoverInfo.object.radiusMiles} Miles</span>
                 </div>
                 <div style={{ display: 'flex', justifyContent: 'space-between', color: 'rgba(255,255,255,0.5)' }}>
                    <span>Network Status:</span>
                    <span style={{ color: '#86efac', fontWeight: 600 }}>{hoverInfo.object.status}</span>
                 </div>
               </div>
             </>
          ) : hoverInfo.object.type === 'STORE' ? (
             <>
               <div style={{ fontWeight: 600, borderBottom: '1px solid rgba(0,255,255,0.3)', paddingBottom: '12px', marginBottom: '12px', fontSize: '0.875rem', color: '#00ffff' }}>
                 WSI Retail Terminal
               </div>
               <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                 <div style={{ fontWeight: 600 }}>{hoverInfo.object.id}</div>
                 <div style={{ display: 'flex', justifyContent: 'space-between', color: 'rgba(255,255,255,0.5)' }}>
                    <span>Supplied By:</span>
                    <span>{hoverInfo.object.suppliedBy}</span>
                 </div>
                 <div style={{ display: 'flex', justifyContent: 'space-between', color: 'rgba(255,255,255,0.5)' }}>
                    <span>Status:</span>
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
