import { useEffect, useMemo, useState } from 'react';
import { Search, PackageSearch } from 'lucide-react';
import { fetchSkuBios } from '../api/skuBioApi';

function formatMoney(value) {
  return `$${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function formatNumber(value, digits = 0) {
  return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: digits });
}

function riskPillColor(riskLevel) {
  if (riskLevel === 'STOCKOUT_RISK') {
    return 'var(--color-stockout-text)';
  }
  if (riskLevel === 'OVERSTOCK_RISK') {
    return 'var(--color-overstock-text, #f59e0b)';
  }
  if (riskLevel === 'WATCH') {
    return 'var(--color-watch-text)';
  }
  return 'var(--color-ok-text)';
}

export default function SkuBio({ selectedDC, selectedSku, setSelectedSku }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('ALL');

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
        if ((payload.records || []).length > 0 && typeof setSelectedSku === 'function' && !selectedSku) {
          setSelectedSku(payload.records[0].sku_id);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load SKU bios');
          setRecords([]);
          if (typeof setSelectedSku === 'function') {
            setSelectedSku('');
          }
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
  }, [selectedDC, setSelectedSku, selectedSku]);

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
    const found = filtered.find((row) => row.sku_id === selectedSku);
    return found || filtered[0];
  }, [filtered, selectedSku]);

  useEffect(() => {
    if (selectedRecord && selectedRecord.sku_id !== selectedSku && typeof setSelectedSku === 'function') {
      setSelectedSku(selectedRecord.sku_id);
    }
  }, [selectedRecord, selectedSku, setSelectedSku]);

  const stockoutCount = records.filter((row) => row.risk_level === 'STOCKOUT_RISK').length;
  const overstockCount = records.filter((row) => row.risk_level === 'OVERSTOCK_RISK').length;
  const avgSurge = records.length
    ? (records.reduce((sum, row) => sum + Number(row.surge_score || 0), 0) / records.length).toFixed(2)
    : '0.00';

  const hotTrendCount = records.filter((row) => row.trend_label === 'Surging' || row.trend_label === 'Accelerating').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '2.3rem', marginBottom: '8px' }}>SKU Atlas</h1>
          <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>
            Structured bios for each SKU from generated inventory + signal datasets.
          </p>
        </div>
        <div style={{ color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
          <PackageSearch size={18} /> Live records: {formatNumber(records.length)}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(160px, 1fr))', gap: '10px' }}>
        <div className="metric-card">
          <div className="metric-title">Total SKU Records</div>
          <div className="metric-value" style={{ fontSize: '1.15rem' }}>{formatNumber(records.length)}</div>
          <div className="metric-trend">Filtered by node: {selectedDC || 'ALL'}</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Stockout Risk</div>
          <div className="metric-value" style={{ fontSize: '1.15rem', color: 'var(--color-stockout-text)' }}>{formatNumber(stockoutCount)}</div>
          <div className="metric-trend">High urgency SKUs</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Overstock Risk</div>
          <div className="metric-value" style={{ fontSize: '1.15rem' }}>{formatNumber(overstockCount)}</div>
          <div className="metric-trend">Rebalancing candidates</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Hot Trend Count</div>
          <div className="metric-value" style={{ fontSize: '1.15rem' }}>{formatNumber(hotTrendCount)}</div>
          <div className="metric-trend">Avg surge: {avgSurge}</div>
        </div>
      </div>

      {error ? (
        <div className="metric-card" style={{ borderColor: 'var(--color-stockout-text)' }}>
          <div style={{ color: 'var(--color-stockout-text)', fontWeight: 600 }}>SKU Atlas error</div>
          <div style={{ color: 'var(--color-text-secondary)', marginTop: '8px' }}>{error}</div>
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: '14px', minHeight: '560px' }}>
        <div className="metric-card" style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflow: 'hidden', padding: '14px' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
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
                placeholder="Search SKU, product, brand"
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

          <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>
            Showing {formatNumber(filtered.length)} records in current scope
          </div>

          <div style={{ overflow: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', paddingRight: '2px' }}>
            {loading ? (
              <div style={{ padding: '12px', color: 'var(--color-text-secondary)' }}>Loading SKU records...</div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: '12px', color: 'var(--color-text-secondary)' }}>No SKU records matched your filters.</div>
            ) : (
              filtered.map((row) => {
                const selected = selectedRecord && selectedRecord.sku_id === row.sku_id;
                return (
                  <button
                    key={`${row.sku_id}-${row.metro}`}
                    onClick={() => {
                      if (typeof setSelectedSku === 'function') {
                        setSelectedSku(row.sku_id);
                      }
                    }}
                    style={{
                      textAlign: 'left',
                      background: selected ? 'var(--color-surface-floating)' : 'transparent',
                      border: `1px solid ${selected ? 'var(--color-primary)' : 'var(--color-surface-hover)'}`,
                      borderRadius: '10px',
                      padding: '10px 11px',
                      cursor: 'pointer',
                      color: 'var(--color-text-primary)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                      <div style={{ fontWeight: 700, fontSize: '0.86rem' }}>{row.sku_id}</div>
                      <span style={{
                        fontSize: '0.68rem',
                        color: riskPillColor(row.risk_level),
                        border: `1px solid ${riskPillColor(row.risk_level)}`,
                        borderRadius: '999px',
                        padding: '2px 8px',
                        fontWeight: 700,
                      }}>
                        {row.risk_level.replace('_', ' ')}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', marginTop: '3px' }}>{row.product_name}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', marginTop: '3px' }}>
                      {row.brand} • {row.category} • {row.metro}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '8px', marginTop: '8px', fontSize: '0.72rem', color: 'var(--color-text-secondary)' }}>
                      <div>Sales7d: {Number(row.sales_velocity_7d || 0).toFixed(1)}%</div>
                      <div>Search7d: {Number(row.search_velocity_7d || 0).toFixed(1)}%</div>
                      <div>DOS: {Number(row.days_of_supply || 0).toFixed(1)}</div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        <div className="metric-card" style={{ overflow: 'auto', padding: '16px' }}>
          {!selectedRecord ? (
            <div style={{ color: 'var(--color-text-secondary)' }}>Select an SKU to see its full profile.</div>
          ) : (
            <>
              <h3 style={{ marginTop: 0, marginBottom: '5px', fontSize: '1.12rem' }}>SKU Profile</h3>
              <div style={{ color: 'var(--color-text-secondary)', marginBottom: '12px', fontSize: '0.88rem' }}>{selectedRecord.sku_id} - {selectedRecord.product_name}</div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(120px, 1fr))', gap: '8px', marginBottom: '12px' }}>
                <div className="metric-card" style={{ padding: '10px' }}>
                  <div className="metric-title">Risk</div>
                  <div className="metric-value" style={{ fontSize: '1rem', color: riskPillColor(selectedRecord.risk_level) }}>{selectedRecord.risk_level.replace('_', ' ')}</div>
                </div>
                <div className="metric-card" style={{ padding: '10px' }}>
                  <div className="metric-title">Trend</div>
                  <div className="metric-value" style={{ fontSize: '1rem' }}>{selectedRecord.trend_label}</div>
                </div>
                <div className="metric-card" style={{ padding: '10px' }}>
                  <div className="metric-title">Price</div>
                  <div className="metric-value" style={{ fontSize: '1rem' }}>{formatMoney(selectedRecord.price)}</div>
                </div>
                <div className="metric-card" style={{ padding: '10px' }}>
                  <div className="metric-title">Surge Score</div>
                  <div className="metric-value" style={{ fontSize: '1rem' }}>{formatNumber(selectedRecord.surge_score, 2)}</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                <div style={{ border: '1px solid var(--color-surface-hover)', borderRadius: '10px', padding: '10px' }}>
                  <div style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', marginBottom: '8px', fontWeight: 700 }}>Identity</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.84rem' }}>
                    <div><strong>Brand:</strong> {selectedRecord.brand}</div>
                    <div><strong>Category:</strong> {selectedRecord.category}</div>
                    <div><strong>Metro:</strong> {selectedRecord.metro}</div>
                    <div><strong>DC:</strong> {selectedRecord.dc}</div>
                    <div><strong>Scenario:</strong> {selectedRecord.scenario_type || '-'}</div>
                    <div><strong>Signal Date:</strong> {selectedRecord.latest_signal_date || '-'}</div>
                  </div>
                </div>

                <div style={{ border: '1px solid var(--color-surface-hover)', borderRadius: '10px', padding: '10px' }}>
                  <div style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', marginBottom: '8px', fontWeight: 700 }}>Inventory</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.84rem' }}>
                    <div><strong>Stock:</strong> {formatNumber(selectedRecord.stock_on_hand)}</div>
                    <div><strong>On Order:</strong> {formatNumber(selectedRecord.on_order)}</div>
                    <div><strong>DOS:</strong> {formatNumber(selectedRecord.days_of_supply, 1)}</div>
                    <div><strong>Lead Time:</strong> {formatNumber(selectedRecord.lead_time_days)}d</div>
                    <div><strong>Daily Sales:</strong> {formatNumber(selectedRecord.avg_daily_sales, 2)}</div>
                    <div><strong>Forecast 60d:</strong> {formatNumber(selectedRecord.forecast_demand_60d)}</div>
                  </div>
                </div>
              </div>

              <div style={{ border: '1px solid var(--color-surface-hover)', borderRadius: '10px', padding: '10px', marginBottom: '10px' }}>
                <div style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', marginBottom: '8px', fontWeight: 700 }}>Demand + Signal Metrics</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '8px', fontSize: '0.84rem' }}>
                  <div><strong>Sales 7d:</strong> {formatNumber(selectedRecord.sales_velocity_7d, 2)}%</div>
                  <div><strong>Search 7d:</strong> {formatNumber(selectedRecord.search_velocity_7d, 2)}%</div>
                  <div><strong>Permit 30d:</strong> {formatNumber(selectedRecord.permit_velocity_30d, 2)}%</div>
                  <div><strong>Composite:</strong> {formatNumber(selectedRecord.composite_score, 2)}</div>
                </div>
              </div>

              <div style={{ border: '1px solid var(--color-surface-hover)', borderRadius: '10px', padding: '10px' }}>
                <div style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', marginBottom: '8px', fontWeight: 700 }}>Operational Guidance</div>
                <div style={{ fontSize: '0.82rem', marginBottom: '6px' }}><strong>Primary Signal:</strong> {selectedRecord.primary_signal || '-'}</div>
                <div style={{ fontSize: '0.82rem', lineHeight: 1.5 }}><strong>Recommended Action:</strong> {selectedRecord.recommended_action || '-'}</div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
