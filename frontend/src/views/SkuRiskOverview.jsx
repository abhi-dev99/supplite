import { useState } from 'react';
import { Filter, Search, Maximize2, X } from 'lucide-react';
import { mockSkus } from '../data';
import SciFiMap from '../components/SciFiMap';
import BrandLogo from '../components/BrandLogo';

export default function SkuRiskOverview({ theme }) {
  const [activeTab, setActiveTab] = useState('ALL');
  const [isMapExpanded, setIsMapExpanded] = useState(false);
  const [isMapHovered, setIsMapHovered] = useState(false);

  const getBadgeClass = (risk) => {
    switch (risk) {
      case 'STOCKOUT_RISK': return 'badge red';
      case 'OVERSTOCK_RISK': return 'badge amber';
      case 'WATCH': return 'badge blue';
      default: return 'badge green';
    }
  };

  const getSupplyWidth = (days) => {
    const max = 120;
    return `${Math.min((days / max) * 100, 100)}%`;
  };

  const tabs = [
    { id: 'ALL', label: 'All Portfolio' },
    { id: 'STOCKOUT_RISK', label: 'Critical Stockouts' },
    { id: 'OVERSTOCK_RISK', label: 'Overstock Surplus' },
    { id: 'WATCH', label: 'Watchlist' }
  ];

  const filteredSkus = mockSkus.filter(sku => {
    if (activeTab === 'ALL') return true;
    return sku.riskLevel === activeTab;
  });

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '40px' }}>
        
        {/* Header Section */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ maxWidth: '600px' }}>
            <h1 style={{ fontSize: '2.5rem', marginBottom: '12px', letterSpacing: '-0.02em', fontFamily: 'var(--font-serif)' }}>
              Risk Overview
            </h1>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: '1.05rem', lineHeight: 1.5, margin: 0 }}>
              Inventory exposure analysis across the primary product ecosystem. Strategic oversight for high-velocity SKUs.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button className="secondary-btn">Export Report</button>
            <button className="action-btn">Initiate Simulation</button>
          </div>
        </div>

        {/* Hero Metrics Row */}
        <div style={{ display: 'flex', gap: '24px' }}>
          
          {/* Core Exposure Box */}
          <div className="metric-card" style={{ flex: 1.5, display: 'flex', flexDirection: 'column', gap: '32px' }}>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)', marginBottom: '12px' }}>
                Core Exposure Metric
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '16px' }}>
                <div style={{ fontSize: '3.5rem', fontFamily: 'var(--font-serif)', fontWeight: 600, color: 'var(--color-text-primary)', lineHeight: 1 }}>
                  $12.4M
                </div>
                <div style={{ color: 'var(--color-stockout-text)', fontWeight: 600, fontSize: '0.875rem' }}>
                  ↗ +12.4% vs LY
                </div>
              </div>
            </div>
            
            <div style={{ display: 'flex', gap: '48px' }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Critical Stockouts</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>14 SKUs</div>
              </div>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Overstock Surplus</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>$4.1M</div>
              </div>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Active Signals</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>128</div>
              </div>
            </div>
          </div>

          {/* Sci-Fi Map Box */}
          <div 
            className="metric-card" 
            style={{ 
              flex: 1, 
              display: 'flex', 
              flexDirection: 'column',
              padding: '16px',
              position: 'relative'
            }}
            onMouseEnter={() => setIsMapHovered(true)}
            onMouseLeave={() => setIsMapHovered(false)}
          >
            <div style={{ padding: '0 8px', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)', marginBottom: '16px' }}>
              North American Logistics Grid
            </div>
            <div style={{ position: 'relative', flex: 1, borderRadius: '8px', overflow: 'hidden' }}>
              <SciFiMap theme={theme} />
              <div style={{
                position: 'absolute',
                top: 0, left: 0, right: 0, bottom: 0,
                backgroundColor: 'rgba(0,0,0,0.5)',
                display: isMapHovered ? 'flex' : 'none',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                transition: 'all 0.2s',
                zIndex: 10
              }} onClick={() => setIsMapExpanded(true)}>
                 <div style={{ 
                   backgroundColor: 'var(--color-primary)', 
                   color: 'var(--color-primary-on)', 
                   padding: '12px 24px', 
                   borderRadius: '4px',
                   display: 'flex',
                   alignItems: 'center',
                   gap: '8px',
                   fontWeight: 600
                 }}>
                    <Maximize2 size={18} /> Expand Immersive View
                 </div>
              </div>
            </div>
          </div>
        </div>

        {/* Table Section */}
        <div className="table-container">
          <div style={{ padding: '24px', borderBottom: '1px solid var(--color-background)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            
            <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
              {tabs.map(tab => (
                <button 
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    padding: '8px 0',
                    color: activeTab === tab.id ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                    borderBottom: activeTab === tab.id ? '2px solid var(--color-text-primary)' : '2px solid transparent',
                    transition: 'all 0.2s'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <div style={{ 
                display: 'flex', alignItems: 'center', backgroundColor: 'var(--color-surface)', 
                padding: '6px 12px', borderRadius: '6px', gap: '8px', width: '200px'
              }}>
                <Search size={14} color="var(--color-text-secondary)" />
                <input 
                  type="text" 
                  placeholder="Search portfolio..." 
                  style={{ border: 'none', background: 'transparent', outline: 'none', fontSize: '0.875rem', width: '100%', color: 'var(--color-text-primary)' }}
                />
              </div>
              <button style={{ padding: '8px', color: 'var(--color-text-secondary)' }}>
                <Filter size={18} />
              </button>
            </div>
          </div>
          
          <table>
            <thead>
              <tr>
                <th>SKU ID</th>
                <th>Product Name</th>
                <th>Brand</th>
                <th>Stock</th>
                <th>Supply</th>
                <th>Risk Status</th>
                <th>Primary Signal</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredSkus.map(sku => (
                <tr key={sku.id} className="table-row-hover">
                  <td style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>{sku.id}</td>
                  <td style={{ maxWidth: '200px' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{sku.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>Category: {sku.category}</div>
                  </td>
                  <td><BrandLogo brand={sku.brand} /></td>
                  <td>{sku.stock.toLocaleString()}</td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{sku.daysOfSupply}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>Days</div>
                  </td>
                  <td>
                    <span className={getBadgeClass(sku.riskLevel)}>
                      {sku.riskLevel.replace('_', ' ')}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>{sku.signal}</td>
                  <td style={{ textAlign: 'right' }}>
                     <div style={{ fontWeight: 600, fontSize: '0.875rem', cursor: 'pointer', color: 'var(--color-primary)' }}>{sku.action}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Fullscreen Map Modal */}
      {isMapExpanded && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: '#000',
          zIndex: 9999,
          display: 'flex'
        }}>
          <button 
            onClick={() => setIsMapExpanded(false)}
            style={{ position: 'absolute', top: '32px', right: '32px', zIndex: 10000, backgroundColor: 'rgba(255,255,255,0.1)', color: '#fff', padding: '12px', borderRadius: '50%' }}
          >
            <X size={24} />
          </button>
          <div style={{ position: 'absolute', top: '32px', left: '32px', zIndex: 10000, color: 'var(--color-text-primary)' }}>
            <h1 style={{ fontSize: '2.5rem', margin: 0, fontFamily: 'var(--font-serif)' }}>Immersive Logistics Grid</h1>
            <p style={{ opacity: 0.7, margin: 0 }}>Showing 2,500 active transit nodes across NA down to ZIP level resolution.</p>
          </div>
          <SciFiMap isFullscreen={true} theme={theme} />
        </div>
      )}
    </>
  );
}
