import { useEffect, useMemo, useState } from 'react';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer, GeoJsonLayer, TextLayer } from '@deck.gl/layers';
import { ContourLayer, HeatmapLayer } from '@deck.gl/aggregation-layers';
import { geoClusters, wsStores, distributionCenters } from '../data';
import { Search } from 'lucide-react';
import stateLabels from '../stateLabels.json';
import { fetchRealEstateHeatmap } from '../api/realEstateApi';

function toArray(value) {
  return Array.isArray(value) ? value : [];
}

const INITIAL_VIEW_STATE = {
  longitude: -96.0,
  latitude: 39.0,
  zoom: 3.2,
  minZoom: 2.5,
  maxZoom: 16,
  pitch: 45,
  bearing: -10
};

function pseudoRandom(seed, step) {
  const value = Math.sin(seed * 12.9898 + step * 78.233) * 43758.5453;
  return value - Math.floor(value);
}

export default function SciFiMap({ isFullscreen = false, theme = 'dark', selectedDC = 'ALL' }) {
  const [hoverInfo, setHoverInfo] = useState(null);
  const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);
  const [searchQuery, setSearchQuery] = useState('');
  const [heatmapPayload, setHeatmapPayload] = useState(null);
  const [heatmapError, setHeatmapError] = useState('');
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showStores, setShowStores] = useState(true);
  const [showDcRadius, setShowDcRadius] = useState(false);
  const [showIntelHub, setShowIntelHub] = useState(false);
  const isDark = theme === 'dark';

  const [usStatesGeoJson, setUsStatesGeoJson] = useState(null);

  useEffect(() => {
    fetch('/us_states.json')
      .then(res => res.json())
      .then(data => {
        data.features = data.features.filter(f => !['Alaska', 'Hawaii', 'Puerto Rico'].includes(f.properties.name));
        setUsStatesGeoJson(data);
      })
      .catch(err => console.error("Could not load US states mapping:", err));

    let cancelled = false;

    async function loadHeatmap() {
      try {
        const payload = await fetchRealEstateHeatmap({ limit: 45000, scope: 'national' });
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

  // Animate map to selected DC location
  useEffect(() => {
    const allDistributionCenters = toArray(distributionCenters);

    if (selectedDC !== 'ALL') {
      const dc = allDistributionCenters.find((d) => d?.name === selectedDC);
      if (dc && dc.coordinates) {
        setViewState((prev) => ({
          ...prev,
          longitude: dc.coordinates[0],
          latitude: dc.coordinates[1],
          zoom: 6.5,
          transitionDuration: 1500
        }));
      }
    } else {
      setViewState((prev) => ({
        ...prev,
        longitude: INITIAL_VIEW_STATE.longitude,
        latitude: INITIAL_VIEW_STATE.latitude,
        zoom: INITIAL_VIEW_STATE.zoom,
        transitionDuration: 1500
      }));
    }
  }, [selectedDC]);

  const clusterData = useMemo(() => {
    // The user ONLY wants data around the 10-11 ML modeled metro areas (DCs). Let's filter visually!
    const allDistributionCenters = toArray(distributionCenters);
    const activeDcNodes = allDistributionCenters.filter((dc) => 
      ['City of Industry DC', 'Braselton DC', 'Dallas DC', 'Litchfield Park DC', 'Oakland, CA', 'Lakeland, FL', 'Denver, CO', 'South Brunswick DC'].includes(dc.name)
    );

    const livePoints = toArray(heatmapPayload?.points);
    const baseData = livePoints.length ? livePoints : toArray(geoClusters);
    
    // Filter base data to only points within ~3.0 degrees (approx 200 miles) of our active modeled metros
    return baseData.filter((point) => {
       const [lng, lat] = point.position || point.coordinates || [];
       if (!Number.isFinite(lng) || !Number.isFinite(lat)) return false;
       
       for (const dc of activeDcNodes) {
          const [dcLng, dcLat] = dc.coordinates || [];
          if (Math.hypot(lng - dcLng, lat - dcLat) <= 4.0) {
             return true;
          }
       }
       return false;
    });
  }, [heatmapPayload]);

  const filteredStores = useMemo(
    () => toArray(wsStores).filter((store) => {
      const name = typeof store?.name === 'string' ? store.name : '';
      return name.toLowerCase().includes(searchQuery.toLowerCase());
    }),
    [searchQuery]
  );

  const heatDensityPoints = useMemo(() => {
    const points = [];
    const largeDataset = clusterData.length > 1200;

    // Densify each scored region into many jittered weighted points.
    clusterData.forEach((cluster, clusterIndex) => {
      const [lng, lat] = cluster.position || [];
      if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
        return;
      }

      const demand = Number(cluster.demand_index || 100);
      const volume = Number(cluster.volume || 120);
      const income = Number(cluster.median_income || 60000);
      
      const riskWeight =
        cluster.risk === 'STOCKOUT_RISK' ? 1.35 : cluster.risk === 'OVERSTOCK_RISK' ? 1.05 : 1.15;
      
      // Affluence Surcharge: Correlation with WSI Brand Value Drivers
      const affluenceSurcharge = income > 150000 ? 1.3 : (income > 100000 ? 1.15 : 1.0);
      const compositeWeight = Math.max(2, demand * riskWeight * affluenceSurcharge);

      const spread = largeDataset
        ? Math.max(0.02, Math.min(0.12, 0.02 + Math.log10(Math.max(volume, 10)) * 0.03))
        : Math.max(0.15, Math.min(0.7, 0.1 + Math.log10(Math.max(volume, 10)) * 0.12));
      
      const copies = largeDataset ? 1 : Math.max(18, Math.min(130, Math.round(15 + demand * 0.4 + volume * 0.015)));

      for (let i = 0; i < copies; i += 1) {
        const angle = pseudoRandom(clusterIndex + 1, i + 11) * Math.PI * 2;
        const radial = Math.pow(pseudoRandom(clusterIndex + 3, i + 19), 0.58) * spread;
        const lngOffset = Math.cos(angle) * radial;
        const latOffset = Math.sin(angle) * radial * 0.75;

        points.push({
          position: [lng + lngOffset, lat + latOffset],
          weight: compositeWeight,
          clusterId: cluster.id,
          isHighIncome: income > 150000
        });
      }
    });

    // Inject network-level points so dense store corridors become visible in the heat surface.
    if (!largeDataset) {
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
    }

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
      // Base geometry for map context
      new GeoJsonLayer({
        id: 'na-geometry',
        data: '/na_map.json',
        stroked: false,
        filled: true,
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
          radiusMaxPixels: 8,
          opacity: 0.75,
          getPosition: (d) => d.position,
          getFillColor: (d) => {
            if (d.risk === 'STOCKOUT_RISK') return [255, 80, 64, 220];
            if (d.risk === 'OVERSTOCK_RISK') return [255, 186, 58, 200];
            return [56, 173, 255, 190];
          },
          getLineColor: (d) => (d.median_income > 160000) ? [74, 222, 128, 255] : [255, 255, 255, 130],
          getLineWidth: (d) => (d.median_income > 160000) ? 200 : 80,
          onHover: (info) => setHoverInfo(info),
        })
      );
    }

    if (showDcRadius) {
      activeLayers.push(
        new ScatterplotLayer({
          id: 'dc-territory-rings',
          data: toArray(distributionCenters),
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
        data: toArray(distributionCenters),
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
          getFillColor: isDark ? [0, 255, 200, 255] : [14, 116, 144, 255],
          onHover: (info) => setHoverInfo(info),
        })
      );
    }
    
    if (usStatesGeoJson) {
      activeLayers.push(
        new GeoJsonLayer({
          id: 'usa-state-lines',
          data: usStatesGeoJson,
          stroked: true,
          filled: false,
          lineWidthMinPixels: 1,
          getLineColor: isDark ? [255, 255, 255, 80] : [0, 0, 0, 40],
        })
      );
    }

    activeLayers.push(
      new TextLayer({
        id: 'usa-state-labels',
        data: toArray(stateLabels).filter((l) => l.name !== 'Alaska' && l.name !== 'Hawaii' && l.name !== 'Puerto Rico'),
        pickable: false,
        getPosition: (d) => d.coordinates,
        getText: (d) => d.name,
        getSize: 22,
        getColor: isDark ? [255, 255, 255, 110] : [15, 23, 42, 160],
        getAngle: 0,
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'center',
        fontFamily: 'var(--font-serif)',
        fontWeight: 'bold',
      })
    );

    return activeLayers;
  }, [clusterData, filteredStores, heatDensityPoints, isDark, isFullscreen, showDcRadius, showHeatmap, showStores, usStatesGeoJson]);

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

  const handleViewStateChange = ({ viewState }) => {
    const minLng = -128, maxLng = -65;
    const minLat = 24, maxLat = 50;

    let lng = Math.max(minLng, Math.min(maxLng, viewState.longitude));
    let lat = Math.max(minLat, Math.min(maxLat, viewState.latitude));

    setViewState({
      ...viewState,
      longitude: lng,
      latitude: lat
    });
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', backgroundColor: isDark ? '#020202' : '#f0f5fa', borderRadius: isFullscreen ? '0' : '8px', overflow: 'hidden' }}>
      <DeckGL
        viewState={viewState}
        onViewStateChange={handleViewStateChange}
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

      {/* Sci-Fi Tooltip HUD */}
      {hoverInfo && hoverInfo.object && (
        <div style={{
          position: 'absolute',
          zIndex: 100,
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
          {hoverInfo.layer.id === 'infrastructure-nodes' || hoverInfo.object.type === 'STORE' ? (
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

                 <div style={{ color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }}>Demand Index:</div>
                 <div style={{ fontWeight: 600 }}>{hoverInfo.object.demand_index ?? 'n/a'}</div>

                 <div style={{ color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }}>Median Income:</div>
                 <div style={{ color: (hoverInfo.object.median_income > 160000) ? '#4ade80' : 'inherit', fontWeight: 600 }}>
                   ${hoverInfo.object.median_income?.toLocaleString() ?? 'n/a'}
                 </div>
                 
                 <div style={{ color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }}>Forecast Delay:</div>
                 <div>{hoverInfo.object.delay}</div>
               </div>
             </>
          )}
        </div>
      )}

      {/* Unified Intelligence Hub Menu */}
      <div 
        style={{
          position: 'absolute', bottom: '24px', left: '24px', zIndex: 110,
        }}
        onMouseEnter={() => setShowIntelHub(true)}
        onMouseLeave={() => setShowIntelHub(false)}
      >
        <button style={{
          backgroundColor: hudSurface,
          color: hudText,
          padding: '12px 22px',
          borderRadius: '30px',
          border: `1px solid ${hudBorder}`,
          backdropFilter: 'blur(15px)',
          fontSize: '0.9rem',
          fontWeight: 600,
          boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          transition: 'all 0.3s ease',
          pointerEvents: 'auto'
        }}>
          <span style={{ fontSize: '1.4rem' }}>⚡</span>
          Intelligence Hub
        </button>

        {showIntelHub && (
          <div style={{
            position: 'absolute', bottom: '100%', left: 0, marginBottom: '14px',
            backgroundColor: hudSurface,
            color: hudText,
            width: '340px',
            borderRadius: '16px',
            border: `1px solid ${hudBorder}`,
            backdropFilter: 'blur(20px)',
            padding: '24px',
            boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
            display: 'flex', flexDirection: 'column', gap: '20px',
            pointerEvents: 'auto'
          }}>
            <div style={{ borderBottom: `1px solid ${hudBorder}`, paddingBottom: '12px' }}>
              <div style={{ fontWeight: 700, fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ opacity: 0.8 }}>ⓘ</span> Data Methodology
              </div>
              <div style={{ fontSize: '0.8rem', color: hudTextMuted, marginTop: '4px' }}>
                Composite Risk & Opportunity Analysis v4.6
              </div>
            </div>

            <section>
              <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '8px', textTransform: 'uppercase', opacity: 0.6 }}>Logic Definitions</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.8rem', lineHeight: 1.4 }}>
                <div><strong>Demand Intensity:</strong> Real-time velocity of search trends & permits.</div>
                <div><strong>Affluence Correlation:</strong> median income {'>'} $110k adds 25% weight surcharge. High affluence nodes marked with <span style={{ color: '#4ade80' }}>green boundaries</span>.</div>
                <div><strong>Logistics Risk:</strong> Factoring distance from Hub centers.</div>
              </div>
            </section>

            <section style={{ borderTop: `1px solid ${hudBorder}`, paddingTop: '16px' }}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '8px', textTransform: 'uppercase', opacity: 0.6 }}>Legend</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.8rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: isDark ? '#00ffff' : '#0e7490' }}/> 
                  <span>Store Node (Current Supply)</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#fff', border: '2px solid #28a0ff' }}/> 
                  <span>Regional Hub / DC</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '12px', height: '10px', borderRadius: '2px', backgroundColor: '#ffb52e' }}/> 
                  <span>Signal Heatmap Intensity</span>
                </div>
              </div>
            </section>

            <div style={{ fontSize: '0.75rem', opacity: 0.6, fontStyle: 'italic', borderTop: `1px solid ${hudBorder}`, paddingTop: '10px' }}>
              Ctrl+Drag to rotate perspective. Geo-fenced to Continental US.
            </div>
            
            <div style={{ color: hudTextMuted, fontSize: '0.75rem', fontWeight: 500 }}>
              {showHeatmap ? `${heatmapLabel} • ${heatDensityPoints.length.toLocaleString()} active signals` : 'Heatmap Layer Deactivated'}
            </div>
          </div>
        )}
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