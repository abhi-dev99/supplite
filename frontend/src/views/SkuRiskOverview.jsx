import { useState } from 'react';
import { Filter, Search, Maximize2, X } from 'lucide-react';
import { mockSkus } from '../data';
import SciFiMap from '../components/SciFiMap';
import BrandLogo from '../components/BrandLogo';

export default function SkuRiskOverview({ theme, selectedDC }) {
  const [activeTab, setActiveTab] = useState('ALL');
  const [isMapExpanded, setIsMapExpanded] = useState(false);
  const [isMapHovered, setIsMapHovered] = useState(false);
  const [hoverTimer, setHoverTimer] = useState(null);

  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getBadgeClass = (risk) => {
    switch (risk) {
      case 'STOCKOUT_RISK': return 'badge red';
      case 'OVERSTOCK_RISK': return 'badge amber';
      case 'WATCH': return 'badge blue';
      default: return 'badge green';
    }
  };

  const tabs = [
    { id: 'ALL', label: 'All Portfolio' },
    { id: 'STOCKOUT_RISK', label: 'Action Required' },
    { id: 'OVERSTOCK_RISK', label: 'Excess Surplus' },
    { id: 'WATCH', label: 'Watchlist' }
  ];

  const filteredSkus = mockSkus.filter(sku => {
    if (activeTab === 'ALL') return true;
    return sku.riskLevel === activeTab;
  });

  const sortedSkus = [...filteredSkus].sort((a, b) => {
    if (!sortConfig.key) return 0;
    
    let aVal = a[sortConfig.key];
    let bVal = b[sortConfig.key];

    if (sortConfig.key === 'stock') {
      aVal = a.stock + a.onOrder;
      bVal = b.stock + b.onOrder;
    }

    if (aVal < bVal) { return sortConfig.direction === 'asc' ? -1 : 1; }
    if (aVal > bVal) { return sortConfig.direction === 'asc' ? 1 : -1; }
    return 0;
  });

  return (
    <>
      <div className="animate-in" style={{ display: 'flex', flexDirection: 'column', gap: '40px' }}>
        
        {/* Header Section */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ maxWidth: '600px' }}>
            <h1 style={{ fontSize: '3rem', marginBottom: '12px', letterSpacing: '-0.02em' }}>
              Intelligence Hub
            </h1>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: '1.1rem', lineHeight: 1.5, margin: 0 }}>
              AI-driven predictive oversight and algorithmic inventory actioning grid.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '16px' }}>
            <button className="action-btn" style={{ background: 'transparent' }}>Export Report</button>
            <button className="action-btn" style={{ background: 'var(--color-primary)', color: 'var(--color-primary-on)', border: 'none' }}>Initiate Auto-Order</button>
          </div>
        </div>

        {/* Hero Metrics Row */}
        <div style={{ display: 'flex', gap: '24px' }}>
          {/* Key Stats Col */}
          <div style={{ flex: 1.2, display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div className="metric-card glass-panel" style={{ flex: 1 }}>
              <div className="metric-title">Critical Shortages Predicted</div>
              <div className="metric-value" style={{ color: 'var(--color-stockout-text)' }}>
                {mockSkus.filter(s => s.riskLevel === 'STOCKOUT_RISK').length} <span style={{ fontSize: '1rem', color: 'var(--color-text-secondary)' }}>Items</span>
              </div>
              <div className="metric-trend" style={{ color: 'var(--color-text-secondary)' }}>Requires immediate action inside 60-day window.</div>
            </div>
            
            <div style={{ display: 'flex', gap: '24px', flex: 1 }}>
              <div className="metric-card glass-panel" style={{ flex: 1, padding: '24px' }}>
                 <div className="metric-title" style={{ fontSize: '0.65rem' }}>Node Capital Exposure</div>
                 <div className="metric-value" style={{ fontSize: '1.75rem' }}>
                   {selectedDC === 'ALL' ? '$12.4M' : '$1.1M'}
                 </div>
                 <div className="metric-trend" style={{ color: 'var(--color-stockout-text)' }}>↗ +12.4% vs LY</div>
              </div>

              <div className="metric-card glass-panel" style={{ flex: 1, padding: '24px' }}>
                 <div className="metric-title" style={{ fontSize: '0.65rem' }}>Trajectory Shifts</div>
                 <div className="metric-value" style={{ fontSize: '1.75rem' }}>{mockSkus.filter(s => s.anomalyFlag).length}</div>
                 <div className="metric-trend" style={{ color: 'var(--color-text-secondary)' }}>Anomalies flagged</div>
              </div>
            </div>
          </div>

          {/* Sci-Fi Map Col */}
          <div 
            className="metric-card glass-panel" 
            style={{ 
              flex: 1, 
              display: 'flex', 
              flexDirection: 'column',
              padding: '16px',
              position: 'relative'
            }}
            onMouseEnter={() => {
              setIsMapHovered(true);
              const timer = setTimeout(() => setIsMapExpanded(true), 400);
              setHoverTimer(timer);
            }}
            onMouseLeave={() => {
              setIsMapHovered(false);
              if (hoverTimer) clearTimeout(hoverTimer);
            }}
          >
            <div style={{ padding: '0 8px', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)', marginBottom: '16px', display: 'flex', justifyContent: 'space-between' }}>
              <span>North American Logistics Grid</span>
              <button 
                onClick={() => setIsMapExpanded(true)}
                style={{
                   background: 'transparent', 
                   color: 'var(--color-text-secondary)',
                   border: 'none',
                   fontSize: '0.65rem',
                   fontWeight: 600,
                   display: 'flex',
                   alignItems: 'center',
                   gap: '4px',
                   cursor: 'pointer',
                   opacity: isMapHovered ? 1 : 0,
                   transition: 'opacity 0.2s',
                   textTransform: 'uppercase'
                }}>
                Hover to Expand <Maximize2 size={12} style={{ marginLeft: '4px'}} />
              </button>
            </div>
            <div style={{ position: 'relative', flex: 1, borderRadius: '8px', overflow: 'hidden' }}>
              <SciFiMap theme={theme} selectedDC={selectedDC} />
            </div>
          </div>
        </div>

        {/* Dynamic Data Grid Section */}
        <div className="glass-panel" style={{ borderRadius: '16px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: '32px' }}>
              {tabs.map(tab => (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  style={{
                    fontSize: '0.875rem', fontWeight: 600, paddingBottom: '8px',
                    color: activeTab === tab.id ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                    borderBottom: activeTab === tab.id ? '2px solid var(--color-text-primary)' : '2px solid transparent',
                    transition: 'all 0.2s'
                  }}>
                  {tab.label}
                </button>
              ))}
            </div>
            
            <div style={{ padding: '10px 16px', background: 'var(--color-background)', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Search size={16} color="var(--color-text-secondary)" />
              <input type="text" placeholder="Search catalog..." style={{ border: 'none', background: 'transparent', outline: 'none', color: 'var(--color-text-primary)', fontSize: '0.875rem' }} />
            </div>
          </div>
          
          {/* List Headers */}
          <div className="data-row-container">
            <div className="data-row-header">
              <div className="data-row-header-item" onClick={() => handleSort('name')}>
                Product Identity {sortConfig.key === 'name' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
              </div>
              <div className="data-row-header-item" onClick={() => handleSort('stock')}>
                Current Stock {sortConfig.key === 'stock' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
              </div>
              <div className="data-row-header-item" onClick={() => handleSort('daysOfSupply')}>
                Runway {sortConfig.key === 'daysOfSupply' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
              </div>
              <div className="data-row-header-item" onClick={() => handleSort('mlForecast60d')}>
                60D Demand {sortConfig.key === 'mlForecast60d' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
              </div>
              <div className="data-row-header-item" onClick={() => handleSort('riskLevel')}>
                Action Status {sortConfig.key === 'riskLevel' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
              </div>
              <div style={{ marginLeft: '16px' }}>AI Reasoning</div>
            </div>

            {/* List Rows */}
            {sortedSkus.map((sku, idx) => (
              <div key={sku.id} className="data-row glass-panel" style={{ animationDelay: `${idx * 0.05}s` }}>
                
                {/* Product Col */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                   <div style={{ opacity: 0.8 }}><BrandLogo brand={sku.brand} /></div>
                   <div>
                     <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--color-text-primary)' }}>{sku.name}</div>
                     <div className="text-sub">{sku.id} • {sku.category}</div>
                   </div>
                </div>

                {/* Stock Col */}
                <div>
                  <div style={{ fontWeight: 600, fontSize: '1rem' }}>
                    {selectedDC === 'ALL' ? (sku.stock + sku.onOrder).toLocaleString() : Math.floor((sku.stock + sku.onOrder) / 11).toLocaleString()}
                  </div>
                  <div className="text-sub">Physical + Pipeline</div>
                </div>

                {/* Runway Col */}
                <div style={{ paddingRight: '24px' }}>
                  <div style={{ fontWeight: 600 }}>{sku.daysOfSupply} Days</div>
                  <div className="runway-bar-bg">
                    <div className="runway-bar-fill" style={{ 
                      width: `${Math.min((sku.daysOfSupply / 120) * 100, 100)}%`,
                      background: sku.daysOfSupply < sku.leadTimeDays ? 'var(--color-stockout-text)' : 'var(--color-ok-text)'
                    }}></div>
                  </div>
                </div>

                {/* Forecast Col */}
                <div>
                   <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                     {selectedDC === 'ALL' ? (sku.mlForecast60d?.toLocaleString() || 0) : Math.floor((sku.mlForecast60d || 0) / 11).toLocaleString()} units
                   </div>
                   <div className="text-sub">
                     {sku.anomalyFlag ? <span style={{ color: '#ef4444' }}>🚨 SPIKING</span> : 'Stable Flightpath'}
                   </div>
                </div>

                {/* Status Col */}
                <div>
                  <span className={getBadgeClass(sku.riskLevel)}>
                    {sku.riskLevel.replace('STOCKOUT_RISK', 'ORDER NOW').replace('OVERSTOCK_RISK', 'HALT ORDERS').replace('_', ' ')}
                  </span>
                </div>

                {/* Reasoning Col */}
                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', lineHeight: 1.5, marginLeft: '16px' }}>
                  {sku.mlReasoning || "Demand remains strictly aligned with historical moving averages."}
                </div>

              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Fullscreen Map Modal */}
      {isMapExpanded && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: '#000', zIndex: 9999, display: 'flex'
        }}>
          <button 
            onClick={() => setIsMapExpanded(false)}
            style={{ position: 'absolute', top: '32px', right: '32px', zIndex: 10000, backgroundColor: 'rgba(255,255,255,0.1)', color: '#fff', padding: '12px', borderRadius: '50%' }}
          >
            <X size={24} />
          </button>
          <div style={{ position: 'absolute', top: '32px', left: '32px', zIndex: 10000, color: 'var(--color-text-primary)' }}>
            <h1 style={{ fontSize: '2.5rem', margin: 0, fontFamily: 'var(--font-serif)' }}>Immersive Logistics Grid</h1>
            <p style={{ opacity: 0.7, margin: 0 }}>Showing active transit nodes across NA down to ZIP level resolution.</p>
          </div>
          <SciFiMap isFullscreen={true} theme={theme} selectedDC={selectedDC} />
        </div>
      )}
    </>
  );
}
