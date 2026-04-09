import { Filter, Search } from 'lucide-react';
import { mockSkus } from '../data';
import RiskHeatmap from '../components/RiskHeatmap';
import BrandLogo from '../components/BrandLogo';

export default function SkuRiskOverview() {
  const getBadgeClass = (risk) => {
    switch (risk) {
      case 'STOCKOUT_RISK': return 'badge red';
      case 'OVERSTOCK_RISK': return 'badge amber';
      case 'WATCH': return 'badge blue';
      default: return 'badge green';
    }
  };

  return (
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

        {/* Heatmap Box */}
        <div className="metric-card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)', marginBottom: '16px' }}>
            Regional Risk Heatmap
          </div>
          <div style={{ flex: 1, display: 'flex', gap: '16px', alignItems: 'center' }}>
            <div style={{ flex: 1 }}>
              <RiskHeatmap />
            </div>
            <div style={{ width: '140px', fontSize: '0.75rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
              Concentrated risk detected in <strong>Northeast Hubs</strong>. Port congestion affecting 14% of transit volume.
            </div>
          </div>
        </div>
      </div>

      {/* Table Section */}
      <div className="table-container">
        <div style={{ padding: '24px', borderBottom: '1px solid var(--color-background)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: '1.25rem', margin: 0, fontFamily: 'var(--font-serif)' }}>Managed Portfolio Inventory</h2>
          
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
            {mockSkus.map(sku => (
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
                   <div style={{ fontWeight: 600, fontSize: '0.875rem', cursor: 'pointer' }}>{sku.action}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        <div style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
          <div>Showing 4 of 129 Critical SKUs</div>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <span style={{ cursor: 'pointer' }}>Previous</span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <span style={{ width: '24px', height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--color-primary)', color: 'var(--color-primary-on)', borderRadius: '4px', fontWeight: 600 }}>1</span>
              <span style={{ width: '24px', height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>2</span>
              <span style={{ width: '24px', height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>3</span>
            </div>
            <span style={{ cursor: 'pointer' }}>Next</span>
          </div>
        </div>

      </div>
    </div>
  );
}
