import { useEffect, useMemo, useState } from 'react';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer, GeoJsonLayer } from '@deck.gl/layers';
import { ContourLayer, HeatmapLayer } from '@deck.gl/aggregation-layers';
import { geoClusters, wsStores, distributionCenters } from '../data';
import { Search } from 'lucide-react';
import { fetchRealEstateHeatmap } from '../api/realEstateApi';

const INITIAL_VIEW_STATE = {
  longitude: -98.0,
  latitude: 38.0,
  zoom: 3.5,
  maxZoom: 16,
  pitch: 50,
  bearing: -10
};

function pseudoRandom(seed, step) {
  const value = Math.sin(seed * 12.9898 + step * 78.233) * 43758.5453;
  return value - Math.floor(value);
}

export default function SciFiMap({ isFullscreen = false, theme = 'dark' }) {
  const [hoverInfo, setHoverInfo] = useState(null);
  const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);
  const [searchQuery, setSearchQuery] = useState('');
  const [heatmapPayload, setHeatmapPayload] = useState(null);
  const [heatmapError, setHeatmapError] = useState('');
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showStores, setShowStores] = useState(true);
  const [showDcRadius, setShowDcRadius] = useState(false);
  const isDark = theme === 'dark';

  useEffect(() => {
    let cancelled = false;

    async function loadHeatmap() {
      try {
        const payload = await fetchRealEstateHeatmap({ limit: 100 });
        if (!cancelled) {
          setHeatmapPayload(payload);
          setHeatmapError('');
        }
      } catch (error) {
        if (!cancelled) {
          setHeatmapError(error instanceof Error ? error.message : 'Heatmap data unavailable');
        }
      }
    }

    loadHeatmap();
    return () => {
      cancelled = true;
    };
  }, []);

  const clusterData = useMemo(() => {
    if (heatmapPayload?.points?.length) {
      return heatmapPayload.points;
    }
    return geoClusters;
  }, [heatmapPayload]);

  const filteredStores = useMemo(
    () => wsStores.filter((store) => store.name.toLowerCase().includes(searchQuery.toLowerCase())),
    [searchQuery]
  );

  const heatDensityPoints = useMemo(() => {
    const points = [];

    // Densify each scored region into many jittered weighted points.
    clusterData.forEach((cluster, clusterIndex) => {
      const [lng, lat] = cluster.position || [];
      if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
        return;
      }

      const demand = Number(cluster.demand_index || 100);
      const volume = Number(cluster.volume || 120);
      const riskWeight =
        cluster.risk === 'STOCKOUT_RISK' ? 1.35 : cluster.risk === 'OVERSTOCK_RISK' ? 1.05 : 1.15;
      const spread = Math.max(0.12, Math.min(0.6, 0.08 + Math.log10(Math.max(volume, 10)) * 0.1));
      const copies = Math.max(24, Math.min(150, Math.round(22 + demand * 0.35 + volume * 0.02)));

      for (let i = 0; i < copies; i += 1) {
        const angle = pseudoRandom(clusterIndex + 1, i + 11) * Math.PI * 2;
        const radial = Math.pow(pseudoRandom(clusterIndex + 3, i + 19), 0.58) * spread;
        const lngOffset = Math.cos(angle) * radial;
        const latOffset = Math.sin(angle) * radial * 0.75;

        points.push({
          position: [lng + lngOffset, lat + latOffset],
          weight: Math.max(2, demand * riskWeight),
          clusterId: cluster.id,
        });
      }
    });

    // Inject network-level points so dense store corridors become visible in the heat surface.
    filteredStores.forEach((store, storeIndex) => {
      if (!Array.isArray(store.coordinates)) {
        return;
      }
      const [storeLng, storeLat] = store.coordinates;
      if (!Number.isFinite(storeLng) || !Number.isFinite(storeLat)) {
        return;
      }

      let nearest = null;
      let nearestDistance = Number.POSITIVE_INFINITY;
      clusterData.forEach((cluster) => {
        const [lng, lat] = cluster.position || [];
        if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
          return;
        }
        const distance = Math.hypot(storeLng - lng, storeLat - lat);
        if (distance < nearestDistance) {
          nearestDistance = distance;
          nearest = cluster;
        }
      });

      const baseDemand = Number(nearest?.demand_index || 100);
      const distanceDecay = Math.max(0.2, 1.0 - nearestDistance * 0.9);
      const storeWeight = Math.max(1.5, baseDemand * distanceDecay * 0.55);

      points.push({
        position: [storeLng, storeLat],
        weight: storeWeight,
        clusterId: nearest?.id || `store-${storeIndex}`,
      });
    });

    return points;
  }, [clusterData, filteredStores]);

  const heatmapLabel = useMemo(() => {
    const primarySource = heatmapPayload?.points?.[0]?.source;
    if (primarySource === 'model-scored-csv') {
      return 'Model-Scored Heatmap';
    }
    if (heatmapPayload?.mode === 'live') {
      return 'Live ACS DP04 Heatmap';
    }
    return 'Fallback Heatmap';
  }, [heatmapPayload]);
  
  const layers = useMemo(() => {
    const activeLayers = [
      // Base geometry for map context.
      new GeoJsonLayer({
        id: 'na-geometry',
        data: '/na_map.json',
        stroked: true,
        filled: true,
        lineWidthMinPixels: 1,
        getLineColor: isDark ? [30, 255, 255, 40] : [0, 80, 150, 40],
        getFillColor: isDark ? [10, 15, 25, 200] : [240, 245, 250, 255],
      }),
    ];

    if (showHeatmap) {
      activeLayers.push(
        new HeatmapLayer({
          id: 'demand-heatmap',
          data: heatDensityPoints,
          pickable: false,
          radiusPixels: isFullscreen ? 62 : 44,
          intensity: 1.1,
          threshold: 0.015,
          colorRange: [
            [16, 78, 139, 60],
            [35, 120, 191, 110],
            [43, 185, 210, 140],
            [53, 220, 92, 160],
            [255, 235, 59, 190],
            [255, 170, 42, 220],
            [255, 85, 28, 240],
          ],
          aggregation: 'SUM',
          getPosition: (d) => d.position,
          getWeight: (d) => d.weight,
        }),
        new ContourLayer({
          id: 'demand-contours',
          data: heatDensityPoints,
          pickable: false,
          cellSize: 18000,
          contours: [
            { threshold: 0.18, color: [255, 255, 255, 80], strokeWidth: 1 },
            { threshold: 0.32, color: [255, 255, 255, 95], strokeWidth: 1 },
            { threshold: 0.48, color: [255, 255, 255, 110], strokeWidth: 1 },
            { threshold: 0.65, color: [255, 255, 255, 130], strokeWidth: 1.2 },
          ],
          getPosition: (d) => d.position,
          getWeight: (d) => d.weight,
        }),
        new ScatterplotLayer({
          id: 'signal-anchors',
          data: clusterData,
          pickable: true,
          stroked: true,
          filled: true,
          radiusScale: 5000,
          radiusMinPixels: 2,
          radiusMaxPixels: 7,
          opacity: 0.65,
          getPosition: (d) => d.position,
          getFillColor: (d) => {
            if (d.risk === 'STOCKOUT_RISK') return [255, 80, 64, 220];
            if (d.risk === 'OVERSTOCK_RISK') return [255, 186, 58, 200];
            return [56, 173, 255, 190];
          },
          getLineColor: [255, 255, 255, 130],
          onHover: (info) => setHoverInfo(info),
        })
      );
    }

    if (showDcRadius) {
      activeLayers.push(
        new ScatterplotLayer({
          id: 'dc-territory-rings',
          data: distributionCenters,
          pickable: false,
          opacity: isDark ? 0.15 : 0.08,
          stroked: true,
          filled: true,
          radiusScale: 1609,
          radiusMinPixels: 10,
          lineWidthMinPixels: 2,
          getPosition: (d) => d.coordinates,
          getRadius: (d) => d.radiusMiles,
          getFillColor: [40, 160, 255],
          getLineColor: [40, 160, 255, 120],
        })
      );
    }

    activeLayers.push(
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
        getPosition: (d) => d.coordinates,
        getFillColor: (d) => {
          if (d.type === 'HQ') return [255, 215, 0];
          if (d.type === 'MFG') return [200, 50, 255];
          return [255, 255, 255];
        },
        getLineColor: (d) => {
          if (d.type === 'HQ') return [255, 180, 0];
          return [40, 160, 255];
        },
        onHover: (info) => setHoverInfo(info),
      })
    );

    if (showStores) {
      activeLayers.push(
        new ScatterplotLayer({
          id: 'store-locations',
          data: filteredStores,
          pickable: true,
          opacity: 0.9,
          stroked: false,
          filled: true,
          radiusScale: 3000,
          radiusMinPixels: 2,
          radiusMaxPixels: 6,
          getPosition: (d) => d.coordinates,
          getFillColor: isDark ? [0, 255, 200, 255] : [0, 150, 150, 255],
          onHover: (info) => setHoverInfo(info),
        })
      );
    }

    return activeLayers;
  }, [clusterData, filteredStores, heatDensityPoints, isDark, isFullscreen, showDcRadius, showHeatmap, showStores]);

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

  const hudSurface = isDark ? 'rgba(8, 10, 16, 0.78)' : 'rgba(255, 255, 255, 0.9)';
  const hudBorder = isDark ? 'rgba(255,255,255,0.12)' : 'rgba(15, 23, 42, 0.1)';
  const hudText = isDark ? 'rgba(255,255,255,0.9)' : 'rgba(18,18,18,0.92)';
  const hudTextMuted = isDark ? 'rgba(255,255,255,0.62)' : 'rgba(18,18,18,0.58)';

  const ToggleChip = ({ label, value, onToggle }) => (
    <button
      type="button"
      onClick={onToggle}
      style={{
        padding: '6px 10px',
        borderRadius: '999px',
        border: `1px solid ${value ? 'rgba(38, 167, 255, 0.5)' : hudBorder}`,
        background: value ? (isDark ? 'rgba(38, 167, 255, 0.2)' : 'rgba(38, 167, 255, 0.14)') : 'transparent',
        color: value ? hudText : hudTextMuted,
        fontSize: '0.72rem',
        fontWeight: 600,
        letterSpacing: '0.02em',
      }}
      aria-pressed={value}
    >
      {label}
    </button>
  );

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
            backgroundColor: hudSurface,
              padding: '8px 16px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '8px',
            border: `1px solid ${hudBorder}`,
            backdropFilter: 'blur(10px)'
          }}>
            <Search size={16} color={hudText} />
              <input 
                  type="text" 
                  placeholder="Find store..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
              style={{ background: 'transparent', border: 'none', color: hudText, outline: 'none', width: '150px' }}
              />
          </div>
      )}

        <div style={{
          position: 'absolute',
          top: isFullscreen ? '100px' : '14px',
          right: isFullscreen ? '24px' : '14px',
          zIndex: 11,
          backgroundColor: hudSurface,
          border: `1px solid ${hudBorder}`,
          borderRadius: '10px',
          backdropFilter: 'blur(10px)',
          padding: '10px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
        <ToggleChip label="Heatmap" value={showHeatmap} onToggle={() => setShowHeatmap((prev) => !prev)} />
        <ToggleChip label="Stores" value={showStores} onToggle={() => setShowStores((prev) => !prev)} />
        <ToggleChip label="DC Radius" value={showDcRadius} onToggle={() => setShowDcRadius((prev) => !prev)} />
        </div>

      {/* Map Legend HUD */}
      <div style={{
          position: 'absolute', bottom: '24px', left: '24px', zIndex: 10,
          backgroundColor: hudSurface,
          padding: '12px', borderRadius: '8px', color: hudText,
          border: `1px solid ${hudBorder}`,
          backdropFilter: 'blur(10px)', fontSize: '0.74rem', display: 'flex', flexDirection: 'column', gap: '6px',
          maxWidth: '220px'
      }}>
          <div style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Map Layers</div>
          <div style={{ color: hudTextMuted }}>Use toggles to focus one signal at a time.</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#00ffff' }}/> Store marker</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#fff', border: '2px solid #28a0ff' }}/> DC node</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><div style={{ width: '10px', height: '8px', borderRadius: '2px', backgroundColor: '#ffb52e' }}/> Heat intensity</div>
      </div>

      <div style={{
          position: 'absolute', bottom: '24px', right: '24px', zIndex: 10,
          backgroundColor: hudSurface,
          padding: '8px 16px', borderRadius: '4px', color: hudTextMuted,
          border: `1px solid ${hudBorder}`,
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
                 <div style={{ fontFamily: 'monospace' }}>{hoverInfo.object.zcta || hoverInfo.object.zipPrefix}</div>
                 
                 <div style={{ color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }}>Risk Class:</div>
                 <div style={{ color: hoverInfo.object.risk === 'STOCKOUT_RISK' ? '#ff3c3c' : hoverInfo.object.risk === 'OVERSTOCK_RISK' ? '#ffb428' : '#28a0ff', fontWeight: 600 }}>
                   {hoverInfo.object.risk.replace('_', ' ')}
                 </div>
                 
                 <div style={{ color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }}>Affected Volume:</div>
                 <div>{hoverInfo.object.volume.toLocaleString()} Units</div>

                 <div style={{ color: 'rgba(255,255,255,0.5)' }}>Demand Index:</div>
                 <div>{hoverInfo.object.demand_index ?? 'n/a'}</div>

                 <div style={{ color: 'rgba(255,255,255,0.5)' }}>Renter Share:</div>
                 <div>{hoverInfo.object.renter_share_pct != null ? `${hoverInfo.object.renter_share_pct}%` : 'n/a'}</div>
                 
                 <div style={{ color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }}>Forecast Delay:</div>
                 <div>{hoverInfo.object.delay}</div>
               </div>
             </>
          )}
        </div>
      )}

      <div style={{
        position: 'absolute',
        right: '12px',
        bottom: '12px',
        zIndex: 20,
        pointerEvents: 'none',
        backgroundColor: hudSurface,
        color: hudText,
        border: `1px solid ${hudBorder}`,
        borderRadius: '6px',
        padding: '6px 10px',
        fontSize: '0.7rem',
        letterSpacing: '0.02em'
      }}>
        {showHeatmap ? `${heatmapLabel} • ${heatDensityPoints.length.toLocaleString()} points` : 'Heatmap hidden'}
        {heatmapError ? ` • ${heatmapError}` : ''}
      </div>
      
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
