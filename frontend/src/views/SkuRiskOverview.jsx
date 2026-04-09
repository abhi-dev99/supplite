import { AlertCircle, DollarSign, PackageX, TrendingUp } from 'lucide-react';
import { mockSkus } from '../data';

export default function SkuRiskOverview() {
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px', letterSpacing: '-0.02em' }}>Demand Intelligence</h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '1.05rem', margin: 0 }}>
            Real-time multi-signal fusion across 847 SKUs
          </p>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px' }}>
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Critical Stockouts</span>
            <PackageX size={18} color="var(--color-stockout-text)" />
          </div>
          <div className="metric-value">12</div>
          <div className="metric-trend"><span style={{color: 'var(--color-stockout-text)'}}>+3</span> since last week</div>
        </div>
        
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Capital at Risk</span>
            <DollarSign size={18} color="var(--color-overstock-text)" />
          </div>
          <div className="metric-value">$4.2M</div>
          <div className="metric-trend"><span style={{color: 'var(--color-text-secondary)'}}>Across 45 overstocked SKUs</span></div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Signals Detected</span>
            <TrendingUp size={18} color="var(--color-watch-text)" />
          </div>
          <div className="metric-value">8</div>
          <div className="metric-trend"><span style={{color: 'var(--color-watch-text)'}}>+14%</span> vs 30-day avg</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Actionable Alerts</span>
            <AlertCircle size={18} color="var(--color-text-primary)" />
          </div>
          <div className="metric-value">24</div>
          <div className="metric-trend">Requiring buyer review today</div>
        </div>
      </div>

      <div className="table-container">
        <div style={{ padding: '24px', borderBottom: '1px solid var(--color-background)', display: 'flex', justifyContent: 'space-between' }}>
          <h2 style={{ fontSize: '1.25rem', margin: 0 }}>SKU Risk Matrix</h2>
          <div style={{ display: 'flex', gap: '8px' }}>
             <button className="secondary-btn">Filter</button>
             <button className="secondary-btn">Export Data</button>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>SKU ID</th>
              <th>Product Details</th>
              <th style={{ width: '200px' }}>Current Supply</th>
              <th>Risk Status</th>
              <th>Primary Signal</th>
              <th style={{ textAlign: 'right' }}>Action Required</th>
            </tr>
          </thead>
          <tbody>
            {mockSkus.map(sku => (
              <tr key={sku.id} className="table-row-hover">
                <td style={{ fontWeight: 600 }}>{sku.id}</td>
                <td>
                  <div style={{ fontWeight: 500, marginBottom: '4px' }}>{sku.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>{sku.brand} • {sku.category}</div>
                </td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600 }}>{sku.daysOfSupply} Days</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>({sku.stock.toLocaleString()} units)</span>
                  </div>
                  <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--color-background)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ 
                      width: getSupplyWidth(sku.daysOfSupply), 
                      height: '100%', 
                      backgroundColor: sku.riskLevel === 'STOCKOUT_RISK' ? 'var(--color-stockout-text)' : 
                                       sku.riskLevel === 'OVERSTOCK_RISK' ? 'var(--color-overstock-text)' : 'var(--color-text-secondary)',
                      borderRadius: '3px'
                    }} />
                  </div>
                </td>
                <td>
                  <span className={getBadgeClass(sku.riskLevel)}>
                    {sku.riskLevel.replace('_', ' ')}
                  </span>
                </td>
                <td style={{ color: 'var(--color-text-secondary)', fontWeight: 500 }}>{sku.signal}</td>
                <td style={{ textAlign: 'right' }}>
                   <button className="action-btn">{sku.action}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
