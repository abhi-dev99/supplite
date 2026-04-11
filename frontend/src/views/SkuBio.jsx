import { useEffect, useMemo, useState } from 'react';
import { Search, PackageSearch } from 'lucide-react';
import { fetchSkuBios } from '../api/skuBioApi';

function formatMoney(value) {
  return `$${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function formatNumber(value, digits = 0) {
  return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: digits });
}

export default function SkuBio({ selectedDC }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [selectedId, setSelectedId] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function loadRecords() {
      setLoading(true);
      try {
        const payload = await fetchSkuBios({ dc: selectedDC || 'ALL' });
        if (cancelled) {
          return;
        }
        setRecords(payload.records || []);
        setError('');
        if ((payload.records || []).length > 0) {
          setSelectedId((current) => current || payload.records[0].sku_id);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load SKU bios');
          setRecords([]);
          setSelectedId('');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadRecords();
    return () => {
      cancelled = true;
    };
  }, [selectedDC]);

  const filtered = useMemo(() => {
    const text = query.trim().toLowerCase();
    return records.filter((row) => {
      if (riskFilter !== 'ALL' && row.risk_level !== riskFilter) {
        return false;
      }
      if (!text) {
        return true;
      }
      return (
        String(row.sku_id || '').toLowerCase().includes(text)
        || String(row.product_name || '').toLowerCase().includes(text)
        || String(row.brand || '').toLowerCase().includes(text)
        || String(row.category || '').toLowerCase().includes(text)
        || String(row.metro || '').toLowerCase().includes(text)
      );
    });
  }, [records, query, riskFilter]);

  const selectedRecord = useMemo(() => {
    if (!filtered.length) {
      return null;
    }
    const found = filtered.find((row) => row.sku_id === selectedId);
    return found || filtered[0];
  }, [filtered, selectedId]);

  useEffect(() => {
    if (selectedRecord && selectedRecord.sku_id !== selectedId) {
      setSelectedId(selectedRecord.sku_id);
    }
  }, [selectedRecord, selectedId]);

  const stockoutCount = records.filter((row) => row.risk_level === 'STOCKOUT_RISK').length;
  const overstockCount = records.filter((row) => row.risk_level === 'OVERSTOCK_RISK').length;
  const avgSurge = records.length
    ? (records.reduce((sum, row) => sum + Number(row.surge_score || 0), 0) / records.length).toFixed(2)
    : '0.00';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>SKU Atlas</h1>
          <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>
            Full bio for each SKU from generated inventory and signal datasets.
          </p>
        </div>
        <div style={{ color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
          <PackageSearch size={18} /> Live records: {formatNumber(records.length)}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(180px, 1fr))', gap: '12px' }}>
        <div className="metric-card">
          <div className="metric-title">Total SKU Records</div>
          <div className="metric-value" style={{ fontSize: '1.3rem' }}>{formatNumber(records.length)}</div>
          <div className="metric-trend">Filtered by node: {selectedDC || 'ALL'}</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Stockout Risk</div>
          <div className="metric-value" style={{ fontSize: '1.3rem', color: 'var(--color-stockout-text)' }}>{formatNumber(stockoutCount)}</div>
          <div className="metric-trend">High urgency SKUs</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Overstock Risk</div>
          <div className="metric-value" style={{ fontSize: '1.3rem' }}>{formatNumber(overstockCount)}</div>
          <div className="metric-trend">Rebalancing candidates</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Average Surge Score</div>
          <div className="metric-value" style={{ fontSize: '1.3rem' }}>{avgSurge}</div>
          <div className="metric-trend">Across current scope</div>
        </div>
      </div>

      {error ? (
        <div className="metric-card" style={{ borderColor: 'var(--color-stockout-text)' }}>
          <div style={{ color: 'var(--color-stockout-text)', fontWeight: 600 }}>SKU Atlas error</div>
          <div style={{ color: 'var(--color-text-secondary)', marginTop: '8px' }}>{error}</div>
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '14px', minHeight: '520px' }}>
        <div className="metric-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflow: 'hidden' }}>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <div style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              borderRadius: '8px',
              background: 'var(--color-surface-floating)',
              border: '1px solid var(--color-surface-hover)',
              padding: '10px 12px',
            }}>
              <Search size={16} color="var(--color-text-secondary)" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search SKU, product, brand, metro"
                style={{ border: 'none', outline: 'none', background: 'transparent', width: '100%', color: 'var(--color-text-primary)' }}
              />
            </div>
            <select
              value={riskFilter}
              onChange={(event) => setRiskFilter(event.target.value)}
              style={{
                minWidth: '170px',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--color-surface-hover)',
                background: 'var(--color-surface-floating)',
                color: 'var(--color-text-primary)',
              }}
            >
              <option value="ALL">All Risk Levels</option>
              <option value="STOCKOUT_RISK">Stockout Risk</option>
              <option value="OVERSTOCK_RISK">Overstock Risk</option>
              <option value="WATCH">Watch</option>
              <option value="OK">OK</option>
            </select>
          </div>

          <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.84rem' }}>
            Showing {formatNumber(filtered.length)} records
          </div>

          <div style={{ overflow: 'auto', border: '1px solid var(--color-surface-hover)', borderRadius: '10px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '940px' }}>
              <thead>
                <tr style={{ background: 'var(--color-surface-floating)' }}>
                  {['SKU', 'Product', 'Brand', 'Category', 'Metro', 'Risk', 'Trend', 'Sales 7d%', 'Search 7d%', 'DOS', 'Lead Time', 'Stock', 'On Order', 'Price'].map((head) => (
                    <th key={head} style={{ textAlign: 'left', padding: '10px 10px', fontSize: '0.78rem', color: 'var(--color-text-secondary)', borderBottom: '1px solid var(--color-surface-hover)' }}>{head}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={14} style={{ padding: '16px', color: 'var(--color-text-secondary)' }}>Loading SKU records...</td></tr>
                ) : filtered.length === 0 ? (
                  <tr><td colSpan={14} style={{ padding: '16px', color: 'var(--color-text-secondary)' }}>No SKU records matched your filters.</td></tr>
                ) : (
                  filtered.map((row) => (
                    <tr
                      key={`${row.sku_id}-${row.metro}`}
                      onClick={() => setSelectedId(row.sku_id)}
                      style={{
                        cursor: 'pointer',
                        background: selectedRecord && selectedRecord.sku_id === row.sku_id ? 'var(--color-surface-floating)' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)', fontWeight: 600 }}>{row.sku_id}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{row.product_name}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{row.brand}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{row.category}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{row.metro}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{row.risk_level}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{row.trend_label}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{Number(row.sales_velocity_7d || 0).toFixed(2)}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{Number(row.search_velocity_7d || 0).toFixed(2)}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{Number(row.days_of_supply || 0).toFixed(1)}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{formatNumber(row.lead_time_days)}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{formatNumber(row.stock_on_hand)}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{formatNumber(row.on_order)}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid var(--color-surface-hover)' }}>{formatMoney(row.price)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="metric-card" style={{ overflow: 'auto' }}>
          {!selectedRecord ? (
            <div style={{ color: 'var(--color-text-secondary)' }}>Select an SKU to see its full profile.</div>
          ) : (
            <>
              <h3 style={{ marginTop: 0, marginBottom: '8px', fontSize: '1.12rem' }}>SKU Profile</h3>
              <div style={{ color: 'var(--color-text-secondary)', marginBottom: '12px' }}>{selectedRecord.sku_id} - {selectedRecord.product_name}</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.88rem' }}>
                <div><strong>Brand:</strong> {selectedRecord.brand}</div>
                <div><strong>Category:</strong> {selectedRecord.category}</div>
                <div><strong>Metro:</strong> {selectedRecord.metro}</div>
                <div><strong>DC:</strong> {selectedRecord.dc}</div>
                <div><strong>Risk Level:</strong> {selectedRecord.risk_level}</div>
                <div><strong>Trend Label:</strong> {selectedRecord.trend_label}</div>
                <div><strong>Price:</strong> {formatMoney(selectedRecord.price)}</div>
                <div><strong>Average Daily Sales:</strong> {formatNumber(selectedRecord.avg_daily_sales, 2)}</div>
                <div><strong>Stock On Hand:</strong> {formatNumber(selectedRecord.stock_on_hand)}</div>
                <div><strong>On Order:</strong> {formatNumber(selectedRecord.on_order)}</div>
                <div><strong>Days Of Supply:</strong> {formatNumber(selectedRecord.days_of_supply, 1)}</div>
                <div><strong>Lead Time (days):</strong> {formatNumber(selectedRecord.lead_time_days)}</div>
                <div><strong>Forecast Demand 60d:</strong> {formatNumber(selectedRecord.forecast_demand_60d)}</div>
                <div><strong>Surge Score:</strong> {formatNumber(selectedRecord.surge_score, 2)}</div>
                <div><strong>Surge Flag:</strong> {selectedRecord.surge_flag}</div>
                <div><strong>Scenario Type:</strong> {selectedRecord.scenario_type || '-'}</div>
                <div><strong>Latest Signal Date:</strong> {selectedRecord.latest_signal_date || '-'}</div>
                <div><strong>Sales Velocity 7d:</strong> {formatNumber(selectedRecord.sales_velocity_7d, 2)}%</div>
                <div><strong>Search Velocity 7d:</strong> {formatNumber(selectedRecord.search_velocity_7d, 2)}%</div>
                <div><strong>Permit Velocity 30d:</strong> {formatNumber(selectedRecord.permit_velocity_30d, 2)}%</div>
                <div><strong>Composite Score:</strong> {formatNumber(selectedRecord.composite_score, 2)}</div>
              </div>

              <div style={{ marginTop: '14px' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Primary Signal</div>
                <div style={{ fontWeight: 600 }}>{selectedRecord.primary_signal || '-'}</div>
              </div>

              <div style={{ marginTop: '12px' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Recommended Action</div>
                <div style={{ lineHeight: 1.5 }}>{selectedRecord.recommended_action || '-'}</div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
