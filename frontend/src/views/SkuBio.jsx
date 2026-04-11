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
  if (riskLevel === 'STOCKOUT_RISK') return 'var(--color-stockout-text)';
  if (riskLevel === 'OVERSTOCK_RISK') return 'var(--color-overstock-text, #f59e0b)';
  if (riskLevel === 'WATCH') return 'var(--color-watch-text)';
  return 'var(--color-ok-text)';
}

function riskRank(riskLevel) {
  if (riskLevel === 'STOCKOUT_RISK') return 0;
  if (riskLevel === 'OVERSTOCK_RISK') return 1;
  if (riskLevel === 'WATCH') return 2;
  return 3;
}

function worstRisk(records) {
  return [...records].sort((a, b) => riskRank(a.risk_level) - riskRank(b.risk_level))[0]?.risk_level || 'OK';
}

export default function SkuBio({ selectedDC, selectedSku, setSelectedSku }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [selectedMetro, setSelectedMetro] = useState('');
  const [profileTab, setProfileTab] = useState('overview');

  useEffect(() => {
    let cancelled = false;
    async function loadRecords() {
      setLoading(true);
      try {
        const payload = await fetchSkuBios({ dc: selectedDC || 'ALL' });
        if (cancelled) return;
        const nextRecords = payload.records || [];
        setRecords(nextRecords);
        setError('');
        if (nextRecords.length > 0 && typeof setSelectedSku === 'function' && !selectedSku) {
          setSelectedSku(nextRecords[0].sku_id);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load SKU bios');
          setRecords([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadRecords();
    return () => {
      cancelled = true;
    };
  }, [selectedDC, setSelectedSku, selectedSku]);

  const skuGroups = useMemo(() => {
    const bySku = new Map();
    records.forEach((row) => {
      if (!bySku.has(row.sku_id)) bySku.set(row.sku_id, []);
      bySku.get(row.sku_id).push(row);
    });

    return [...bySku.entries()].map(([sku_id, skuRecords]) => {
      const first = skuRecords[0];
      const avgSurge = skuRecords.reduce((sum, row) => sum + Number(row.surge_score || 0), 0) / Math.max(1, skuRecords.length);
      return {
        sku_id,
        product_name: first.product_name,
        brand: first.brand,
        category: first.category,
        worst_risk: worstRisk(skuRecords),
        avg_surge: avgSurge,
        metro_count: skuRecords.length,
        records: skuRecords,
      };
    });
  }, [records]);

  const filteredSkus = useMemo(() => {
    const text = query.trim().toLowerCase();
    return skuGroups
      .filter((sku) => {
        if (riskFilter !== 'ALL' && sku.worst_risk !== riskFilter) return false;
        if (!text) return true;
        const metroText = sku.records.map((item) => item.metro).join(' ').toLowerCase();
        return (
          sku.sku_id.toLowerCase().includes(text)
          || String(sku.product_name || '').toLowerCase().includes(text)
          || String(sku.brand || '').toLowerCase().includes(text)
          || String(sku.category || '').toLowerCase().includes(text)
          || metroText.includes(text)
        );
      })
      .sort((a, b) => {
        const rankDiff = riskRank(a.worst_risk) - riskRank(b.worst_risk);
        if (rankDiff !== 0) return rankDiff;
        return b.avg_surge - a.avg_surge;
      });
  }, [skuGroups, query, riskFilter]);

  const selectedSkuGroup = useMemo(() => {
    if (!filteredSkus.length) return null;
    return filteredSkus.find((sku) => sku.sku_id === selectedSku) || filteredSkus[0];
  }, [filteredSkus, selectedSku]);

  useEffect(() => {
    if (selectedSkuGroup && selectedSkuGroup.sku_id !== selectedSku && typeof setSelectedSku === 'function') {
      setSelectedSku(selectedSkuGroup.sku_id);
    }
  }, [selectedSkuGroup, selectedSku, setSelectedSku]);

  const metroOptions = selectedSkuGroup ? selectedSkuGroup.records.map((item) => item.metro) : [];

  useEffect(() => {
    if (!metroOptions.length) {
      setSelectedMetro('');
      return;
    }
    if (!metroOptions.includes(selectedMetro)) {
      setSelectedMetro(metroOptions[0]);
    }
  }, [metroOptions, selectedMetro]);

  const selectedRecord = useMemo(() => {
    if (!selectedSkuGroup) return null;
    return selectedSkuGroup.records.find((item) => item.metro === selectedMetro) || selectedSkuGroup.records[0] || null;
  }, [selectedSkuGroup, selectedMetro]);

  const stockoutCount = skuGroups.filter((sku) => sku.worst_risk === 'STOCKOUT_RISK').length;
  const overstockCount = skuGroups.filter((sku) => sku.worst_risk === 'OVERSTOCK_RISK').length;
  const hotTrendCount = records.filter((row) => row.trend_label === 'Surging' || row.trend_label === 'Accelerating').length;
  const avgSurge = records.length
    ? (records.reduce((sum, row) => sum + Number(row.surge_score || 0), 0) / records.length).toFixed(2)
    : '0.00';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '2.25rem', marginBottom: '8px' }}>SKU Atlas</h1>
          <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>
            One profile per SKU, then drill into metro-level details.
          </p>
        </div>
        <div style={{ color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
          <PackageSearch size={18} /> Unique SKUs: {formatNumber(skuGroups.length)}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(160px, 1fr))', gap: '10px' }}>
        <div className="metric-card">
          <div className="metric-title">Total SKU Profiles</div>
          <div className="metric-value" style={{ fontSize: '1.1rem' }}>{formatNumber(skuGroups.length)}</div>
          <div className="metric-trend">Node scope: {selectedDC || 'ALL'}</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Stockout-Risk SKUs</div>
          <div className="metric-value" style={{ fontSize: '1.1rem', color: 'var(--color-stockout-text)' }}>{formatNumber(stockoutCount)}</div>
          <div className="metric-trend">Most urgent bucket</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Overstock-Risk SKUs</div>
          <div className="metric-value" style={{ fontSize: '1.1rem' }}>{formatNumber(overstockCount)}</div>
          <div className="metric-trend">Capital tie-up candidates</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Signal Heat</div>
          <div className="metric-value" style={{ fontSize: '1.1rem' }}>{formatNumber(hotTrendCount)}</div>
          <div className="metric-trend">Avg surge: {avgSurge}</div>
        </div>
      </div>

      {error ? (
        <div className="metric-card" style={{ borderColor: 'var(--color-stockout-text)' }}>
          <div style={{ color: 'var(--color-stockout-text)', fontWeight: 600 }}>SKU Atlas error</div>
          <div style={{ color: 'var(--color-text-secondary)', marginTop: '8px' }}>{error}</div>
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '14px', minHeight: '560px' }}>
        <div className="metric-card" style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflow: 'hidden', padding: '14px' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <div
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                borderRadius: '8px',
                background: 'var(--color-surface-floating)',
                border: '1px solid var(--color-surface-hover)',
                padding: '10px 12px',
              }}
            >
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
                minWidth: '150px',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--color-surface-hover)',
                background: 'var(--color-surface-floating)',
                color: 'var(--color-text-primary)',
              }}
            >
              <option value="ALL">All Risk</option>
              <option value="STOCKOUT_RISK">Stockout Risk</option>
              <option value="OVERSTOCK_RISK">Overstock Risk</option>
              <option value="WATCH">Watch</option>
              <option value="OK">OK</option>
            </select>
          </div>

          <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>
            Showing {formatNumber(filteredSkus.length)} SKU profiles
          </div>

          <div style={{ overflow: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', paddingRight: '2px' }}>
            {loading ? (
              <div style={{ padding: '12px', color: 'var(--color-text-secondary)' }}>Loading SKU records...</div>
            ) : filteredSkus.length === 0 ? (
              <div style={{ padding: '12px', color: 'var(--color-text-secondary)' }}>No SKU profiles matched your filters.</div>
            ) : (
              filteredSkus.map((sku) => {
                const selected = selectedSkuGroup && selectedSkuGroup.sku_id === sku.sku_id;
                return (
                  <button
                    key={sku.sku_id}
                    onClick={() => {
                      if (typeof setSelectedSku === 'function') setSelectedSku(sku.sku_id);
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
                      <div style={{ fontWeight: 700, fontSize: '0.86rem' }}>{sku.sku_id}</div>
                      <span
                        style={{
                          fontSize: '0.67rem',
                          color: riskPillColor(sku.worst_risk),
                          border: `1px solid ${riskPillColor(sku.worst_risk)}`,
                          borderRadius: '999px',
                          padding: '2px 8px',
                          fontWeight: 700,
                        }}
                      >
                        {sku.worst_risk.replace('_', ' ')}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', marginTop: '3px' }}>{sku.product_name}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', marginTop: '3px' }}>
                      {sku.brand} • {sku.category} • {sku.metro_count} metros
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        <div className="metric-card" style={{ overflow: 'auto', padding: '16px' }}>
          {!selectedRecord ? (
            <div style={{ color: 'var(--color-text-secondary)' }}>Select an SKU profile to view details.</div>
          ) : (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px', flexWrap: 'wrap' }}>
                <div>
                  <h3 style={{ marginTop: 0, marginBottom: '5px', fontSize: '1.12rem' }}>SKU Profile</h3>
                  <div style={{ color: 'var(--color-text-secondary)', marginBottom: '10px', fontSize: '0.88rem' }}>
                    {selectedRecord.sku_id} - {selectedRecord.product_name}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Metro</div>
                  <select
                    value={selectedMetro}
                    onChange={(event) => setSelectedMetro(event.target.value)}
                    style={{
                      minWidth: '180px',
                      padding: '8px 10px',
                      borderRadius: '8px',
                      border: '1px solid var(--color-surface-hover)',
                      background: 'var(--color-surface-floating)',
                      color: 'var(--color-text-primary)',
                    }}
                  >
                    {metroOptions.map((metro) => (
                      <option key={metro} value={metro}>{metro}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                {['overview', 'inventory', 'signals', 'action'].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setProfileTab(tab)}
                    style={{
                      border: '1px solid var(--color-surface-hover)',
                      borderRadius: '999px',
                      padding: '6px 10px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      color: profileTab === tab ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                      background: profileTab === tab ? 'var(--color-surface-floating)' : 'transparent',
                    }}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {profileTab === 'overview' ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(120px, 1fr))', gap: '8px' }}>
                  <div className="metric-card" style={{ padding: '10px' }}>
                    <div className="metric-title">Risk</div>
                    <div className="metric-value" style={{ fontSize: '0.98rem', color: riskPillColor(selectedRecord.risk_level) }}>{selectedRecord.risk_level.replace('_', ' ')}</div>
                  </div>
                  <div className="metric-card" style={{ padding: '10px' }}>
                    <div className="metric-title">Trend</div>
                    <div className="metric-value" style={{ fontSize: '0.98rem' }}>{selectedRecord.trend_label}</div>
                  </div>
                  <div className="metric-card" style={{ padding: '10px' }}>
                    <div className="metric-title">Price</div>
                    <div className="metric-value" style={{ fontSize: '0.98rem' }}>{formatMoney(selectedRecord.price)}</div>
                  </div>
                  <div className="metric-card" style={{ padding: '10px' }}>
                    <div className="metric-title">Surge Score</div>
                    <div className="metric-value" style={{ fontSize: '0.98rem' }}>{formatNumber(selectedRecord.surge_score, 2)}</div>
                  </div>
                  <div style={{ border: '1px solid var(--color-surface-hover)', borderRadius: '10px', padding: '10px', gridColumn: '1 / -1' }}>
                    <div style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', marginBottom: '8px', fontWeight: 700 }}>Identity</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', fontSize: '0.84rem' }}>
                      <div><strong>Brand:</strong> {selectedRecord.brand}</div>
                      <div><strong>Category:</strong> {selectedRecord.category}</div>
                      <div><strong>DC:</strong> {selectedRecord.dc}</div>
                      <div><strong>Scenario:</strong> {selectedRecord.scenario_type || '-'}</div>
                      <div><strong>Signal Date:</strong> {selectedRecord.latest_signal_date || '-'}</div>
                      <div><strong>Metro Coverage:</strong> {formatNumber(metroOptions.length)}</div>
                    </div>
                  </div>
                </div>
              ) : null}

              {profileTab === 'inventory' ? (
                <div style={{ border: '1px solid var(--color-surface-hover)', borderRadius: '10px', padding: '10px' }}>
                  <div style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', marginBottom: '8px', fontWeight: 700 }}>Inventory and Supply Posture</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.84rem' }}>
                    <div><strong>Stock On Hand:</strong> {formatNumber(selectedRecord.stock_on_hand)}</div>
                    <div><strong>On Order:</strong> {formatNumber(selectedRecord.on_order)}</div>
                    <div><strong>Days of Supply:</strong> {formatNumber(selectedRecord.days_of_supply, 1)}</div>
                    <div><strong>Lead Time:</strong> {formatNumber(selectedRecord.lead_time_days)} days</div>
                    <div><strong>Average Daily Sales:</strong> {formatNumber(selectedRecord.avg_daily_sales, 2)}</div>
                    <div><strong>Forecast 60d:</strong> {formatNumber(selectedRecord.forecast_demand_60d)}</div>
                  </div>
                </div>
              ) : null}

              {profileTab === 'signals' ? (
                <div style={{ border: '1px solid var(--color-surface-hover)', borderRadius: '10px', padding: '10px' }}>
                  <div style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', marginBottom: '8px', fontWeight: 700 }}>Demand and Signal Diagnostics</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(120px, 1fr))', gap: '8px', fontSize: '0.84rem' }}>
                    <div><strong>Sales Velocity 7d:</strong><br />{formatNumber(selectedRecord.sales_velocity_7d, 2)}%</div>
                    <div><strong>Search Velocity 7d:</strong><br />{formatNumber(selectedRecord.search_velocity_7d, 2)}%</div>
                    <div><strong>Permit Velocity 30d:</strong><br />{formatNumber(selectedRecord.permit_velocity_30d, 2)}%</div>
                    <div><strong>Composite Score:</strong><br />{formatNumber(selectedRecord.composite_score, 2)}</div>
                  </div>
                </div>
              ) : null}

              {profileTab === 'action' ? (
                <div style={{ border: '1px solid var(--color-surface-hover)', borderRadius: '10px', padding: '10px' }}>
                  <div style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', marginBottom: '8px', fontWeight: 700 }}>Operational Guidance</div>
                  <div style={{ fontSize: '0.83rem', marginBottom: '8px' }}><strong>Primary Signal:</strong> {selectedRecord.primary_signal || '-'}</div>
                  <div style={{ fontSize: '0.83rem', lineHeight: 1.5 }}><strong>Recommended Action:</strong> {selectedRecord.recommended_action || '-'}</div>
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
