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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      <div>
        <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>SKU Risk Overview</h1>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: '1rem', margin: 0 }}>
          Multi-signal fusion tracking 800+ SKUs across 9 WSI brands.
        </p>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>SKU ID</th>
              <th>Product Name</th>
              <th>Brand</th>
              <th>Category</th>
              <th>Stock</th>
              <th>Supply</th>
              <th>Risk Status</th>
              <th>Primary Signal</th>
              <th>Action Required</th>
            </tr>
          </thead>
          <tbody>
            {mockSkus.map(sku => (
              <tr key={sku.id} style={{ cursor: 'pointer' }}>
                <td style={{ fontWeight: 600 }}>{sku.id}</td>
                <td>{sku.name}</td>
                <td style={{ color: 'var(--color-text-secondary)' }}>{sku.brand}</td>
                <td style={{ color: 'var(--color-text-secondary)' }}>{sku.category}</td>
                <td>{sku.stock.toLocaleString()}</td>
                <td style={{ fontWeight: 500 }}>{sku.daysOfSupply} Days</td>
                <td>
                  <span className={getBadgeClass(sku.riskLevel)}>
                    {sku.riskLevel.replace('_', ' ')}
                  </span>
                </td>
                <td style={{ color: 'var(--color-text-secondary)' }}>{sku.signal}</td>
                <td style={{ fontWeight: 600 }}>{sku.action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
