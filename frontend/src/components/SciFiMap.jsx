import { useState } from 'react';
import DeckGL from '@deck.gl/react';
import { ColumnLayer, ScatterplotLayer, GeoJsonLayer } from '@deck.gl/layers';
import { geoClusters, wsStores, distributionCenters } from '../data';
import { Search } from 'lucide-react';

const INITIAL_VIEW_STATE = {
  longitude: -98.0,
  latitude: 38.0,
  zoom: 3.5,
  maxZoom: 16,
  pitch: 50,
  bearing: -10
};

export default function SciFiMap({ isFullscreen = false, theme = 'dark' }) {
  const [hoverInfo, setHoverInfo] = useState(null);
  const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);
  const [searchQuery, setSearchQuery] = useState('');
  
  const isDark = theme === 'dark';
  
  const layers = [
    // 1. The Base Map holding North America geometry
    new GeoJsonLayer({
      id: 'na-geometry',
      data: '/na_map.json',
      stroked: true,
      filled: true,
      lineWidthMinPixels: 1,
      getLineColor: isDark ? [30, 255, 255, 40] : [0, 80, 150, 40], 
      getFillColor: isDark ? [10, 15, 25, 200] : [240, 245, 250, 255], 
    }),

    // 2. The Service Territory Radars (Massive translucent circles around DCs)
    new ScatterplotLayer({
      id: 'dc-territory-rings',
      data: distributionCenters,
      pickable: false,
      opacity: isDark ? 0.15 : 0.08,
      stroked: true,
      filled: true,
      radiusScale: 1609, // Convert miles to meters
      radiusMinPixels: 10,
      lineWidthMinPixels: 2,
      getPosition: d => d.coordinates,
      getRadius: d => d.radiusMiles,
      getFillColor: [40, 160, 255], 
      getLineColor: [40, 160, 255, 120], 
    }),

    // 3. The Supply Chain Infrastructure Nodes (DCs, Hubs, Mfg, HQ)
    new ScatterplotLayer({
      id: 'infrastructure-nodes',
      data: distributionCenters,
      pickable: true,
      opacity: 1,
      stroked: true,
      filled: true,
      radiusScale: 8000,
      radiusMinPixels: 5,
      radiusMaxPixels: 12,
      lineWidthMinPixels: 2,
      getPosition: d => d.coordinates,
      getFillColor: d => {
         if(d.type === 'HQ') return [255, 215, 0]; // Gold for HQ
         if(d.type === 'MFG') return [200, 50, 255]; // Purple for manufacturing
         return [255, 255, 255]; // White for others
      }, 
      getLineColor: d => {
         if(d.type === 'HQ') return [255, 180, 0];
         return [40, 160, 255]; 
      },
      onHover: info => setHoverInfo(info)
    }),

    // 4. The WSI Retail Storefronts
    new ScatterplotLayer({
      id: 'store-locations',
      data: wsStores.filter(s => s.name.toLowerCase().includes(searchQuery.toLowerCase())),
      pickable: true,
      opacity: 0.9,
      stroked: false,
      filled: true,
      radiusScale: 3000,
      radiusMinPixels: 2,
      radiusMaxPixels: 6,
      getPosition: d => d.coordinates,
      getFillColor: isDark ? [0, 255, 200, 255] : [0, 150, 150, 255], 
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
        if (d.risk === 'STOCKOUT_RISK') return [255, 60, 60, 220]; 
        if (d.risk === 'OVERSTOCK_RISK') return [255, 180, 40, 220]; 
        return [40, 160, 255, 220]; 
      },
      getElevation: d => d.volume,
      onHover: info => setHoverInfo(info)
    })
  ];

  const getLabelForType = (type) => {
      switch(type) {
         case 'STORE': return 'WSI Retail Terminal';
         case 'HQ': return 'Global Headquarters';
         case 'DC': return 'Distribution Center';
         case 'HUB': return 'Distribution Hub';
         case 'MFG': return 'Manufacturing Facility';
         case 'CARE': return 'Customer Care Center';
         default: return 'Logistics Node';
      }
  };

  const getLabelColor = (type) => {
      if(type === 'HQ') return '#ffd700';
      if(type === 'MFG') return '#c832ff';
      if(type === 'STORE') return '#00ffff';
      return '#4fc3f7';
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', backgroundColor: isDark ? '#020202' : '#f0f5fa', borderRadius: isFullscreen ? '0' : '8px', overflow: 'hidden' }}>
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState }) => setViewState(viewState)}
        controller={{ dragRotate: true, dragPan: true, touchRotate: true, doubleClickZoom: true, keyboard: true }}
        layers={layers}
      />
      
      {/* Search Bar HUD */}
      {isFullscreen && (
          <div style={{
              position: 'absolute', top: '100px', left: '32px', zIndex: 10,
              backgroundColor: isDark ? 'rgba(5, 5, 10, 0.8)' : 'rgba(255, 255, 255, 0.9)',
              padding: '8px 16px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '8px',
              border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`
          }}>
              <Search size={16} color={isDark ? '#fff' : '#000'} />
              <input 
                  type="text" 
                  placeholder="Find store..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ background: 'transparent', border: 'none', color: isDark ? '#fff' : '#000', outline: 'none', width: '150px' }}
              />
          </div>
      )}

      {/* Map Legend HUD */}
      <div style={{
          position: 'absolute', bottom: '24px', left: '24px', zIndex: 10,
          backgroundColor: isDark ? 'rgba(5, 5, 10, 0.8)' : 'rgba(255, 255, 255, 0.9)',
          padding: '16px', borderRadius: '8px', color: isDark ? '#fff' : '#000',
          border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
          backdropFilter: 'blur(10px)', fontSize: '0.75rem', display: 'flex', flexDirection: 'column', gap: '8px'
      }}>
          <div style={{ fontWeight: 600, marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Network Legend</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#ffd700' }}/> Global Headquarters</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#fff', border: '2px solid #28a0ff' }}/> Distribution Center</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#c832ff' }}/> Manufacturing</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#00ffff' }}/> Retail Storefront</div>
          
          <div style={{ fontWeight: 600, marginTop: '8px', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Risk Volumes</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><div style={{ width: '8px', height: '12px', backgroundColor: '#ff3c3c' }}/> Critical Stockout</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><div style={{ width: '8px', height: '12px', backgroundColor: '#28a0ff' }}/> Stable Supply</div>
      </div>

      <div style={{
          position: 'absolute', bottom: '24px', right: '24px', zIndex: 10,
          backgroundColor: isDark ? 'rgba(5, 5, 10, 0.8)' : 'rgba(255, 255, 255, 0.9)',
          padding: '8px 16px', borderRadius: '4px', color: isDark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.6)',
          border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
          backdropFilter: 'blur(10px)', fontSize: '0.75rem',
      }}>
          <strong>Ctrl+Drag</strong> or <strong>Right-Click+Drag</strong> to Rotate 3D
      </div>
      
      {/* Sci-Fi Tooltip HUD */}
      {hoverInfo && hoverInfo.object && (
        <div style={{
          position: 'absolute',
          zIndex: 15,
          pointerEvents: 'none',
          left: hoverInfo.x,
          top: hoverInfo.y,
          backgroundColor: isDark ? 'rgba(5, 5, 10, 0.95)' : 'rgba(255, 255, 255, 0.95)',
          padding: '16px',
          color: isDark ? '#fff' : '#000',
          borderRadius: '6px',
          border: `1px solid ${isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)'}`,
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
          fontSize: '0.75rem',
          transform: 'translate(-50%, -120%)',
          width: '260px',
          fontFamily: 'var(--font-sans)',
          backdropFilter: 'blur(10px)'
        }}>
          {hoverInfo.layer.id === 'dc-nodes' || hoverInfo.layer.id === 'infrastructure-nodes' || hoverInfo.object.type === 'STORE' ? (
             <>
               <div style={{ fontWeight: 600, borderBottom: `1px solid ${getLabelColor(hoverInfo.object.type)}40`, paddingBottom: '12px', marginBottom: '12px', fontSize: '0.875rem', color: getLabelColor(hoverInfo.object.type) }}>
                 {getLabelForType(hoverInfo.object.type)}
               </div>
               <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                 <div style={{ fontWeight: 600 }}>{hoverInfo.object.name}</div>
                 {hoverInfo.object.radiusMiles > 0 && (
                   <div style={{ display: 'flex', justifyContent: 'space-between', color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }}>
                      <span>Territory Radius:</span>
                      <span>{hoverInfo.object.radiusMiles} Miles</span>
                   </div>
                 )}
                 {hoverInfo.object.status && (
                   <div style={{ display: 'flex', justifyContent: 'space-between', color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }}>
                      <span>Status:</span>
                      <span style={{ color: '#00c853', fontWeight: 600 }}>{hoverInfo.object.status}</span>
                   </div>
                 )}
               </div>
             </>
          ) : (
             <>
               <div style={{ fontWeight: 600, borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`, paddingBottom: '12px', marginBottom: '12px', fontSize: '0.875rem' }}>
                 Signal Cluster: {hoverInfo.object.hub}
               </div>
               <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                 <div style={{ color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }}>ZIP Sector:</div>
                 <div style={{ fontFamily: 'monospace' }}>{hoverInfo.object.zipPrefix}</div>
                 
                 <div style={{ color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }}>Risk Class:</div>
                 <div style={{ color: hoverInfo.object.risk === 'STOCKOUT_RISK' ? '#ff3c3c' : hoverInfo.object.risk === 'OVERSTOCK_RISK' ? '#ffb428' : '#28a0ff', fontWeight: 600 }}>
                   {hoverInfo.object.risk.replace('_', ' ')}
                 </div>
                 
                 <div style={{ color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }}>Affected Volume:</div>
                 <div>{hoverInfo.object.volume.toLocaleString()} Units</div>
                 
                 <div style={{ color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }}>Forecast Delay:</div>
                 <div>{hoverInfo.object.delay}</div>
               </div>
             </>
          )}
        </div>
      )}
      
      {/* Vignette Overlay */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0, bottom: 0,
        pointerEvents: 'none',
        background: isDark ? 'radial-gradient(circle at center, transparent 30%, rgba(0, 0, 0, 0.4) 100%)' : 'none',
        boxShadow: isDark ? 'inset 0 0 100px rgba(0,0,0,0.9)' : 'inset 0 0 50px rgba(0,0,0,0.1)'
      }} />
    </div>
  );
}
