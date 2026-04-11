import { useEffect, useMemo, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Sliders, TrendingUp, DollarSign } from 'lucide-react';
import { fetchEarlyCatchSimulation, fetchSimulationOptions } from '../api/simulationApi';

function formatMoney(value) {
  const num = Number(value || 0);
  return `$${num.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function formatPct(value) {
  const num = Number(value || 0);
  return `${num.toFixed(2)}%`;
}

function formatDateLabel(value) {
  const text = String(value || '');
  if (text.length >= 10) {
    return text.slice(5);
  }
  return text;
}

function dedupeSkuOptions(options) {
  const map = new Map();
  options.forEach((option) => {
    if (!map.has(option.sku_id)) {
      map.set(option.sku_id, option);
    }
  });
  return [...map.values()];
}

export default function Simulation({ selectedDC }) {
  const [options, setOptions] = useState([]);
  const [selectedSku, setSelectedSku] = useState('');
  const [selectedMetro, setSelectedMetro] = useState('');
  const [horizonDays, setHorizonDays] = useState(60);
  const [baselineLagDays, setBaselineLagDays] = useState(14);
  const [earlierByDays, setEarlierByDays] = useState(8);
  const [marginRate, setMarginRate] = useState(0.42);
  const [simulation, setSimulation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function loadOptions() {
      try {
        const payload = await fetchSimulationOptions({ dc: selectedDC || 'ALL' });
        if (cancelled) {
          return;
        }
        const skuOptions = payload.sku_options || [];
        setOptions(skuOptions);

        const defaultOption = skuOptions[0] || null;
        if (defaultOption) {
          setSelectedSku((current) => current || defaultOption.sku_id);
          setSelectedMetro((current) => current || defaultOption.metro);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load simulation options');
          setOptions([]);
        }
      }
    }

    loadOptions();
    return () => {
      cancelled = true;
    };
  }, [selectedDC]);

  const skuOptions = useMemo(() => dedupeSkuOptions(options), [options]);

  const metrosForSku = useMemo(
    () => options.filter((item) => item.sku_id === selectedSku).map((item) => item.metro),
    [options, selectedSku],
  );

  useEffect(() => {
    if (!selectedSku) {
      return;
    }
    if (!metrosForSku.includes(selectedMetro)) {
      setSelectedMetro(metrosForSku[0] || '');
    }
  }, [selectedSku, selectedMetro, metrosForSku]);

  useEffect(() => {
    if (!selectedSku || !selectedMetro) {
      return;
    }

    let cancelled = false;
    async function loadSimulation() {
      setLoading(true);
      try {
        const payload = await fetchEarlyCatchSimulation({
          skuId: selectedSku,
          metro: selectedMetro,
          horizonDays,
          baselineLagDays,
          earlierByDays,
          marginRate,
        });

        if (!cancelled) {
          setSimulation(payload);
          setError('');
        }
      } catch (err) {
        if (!cancelled) {
          setSimulation(null);
          setError(err instanceof Error ? err.message : 'Failed to run simulation');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadSimulation();
    return () => {
      cancelled = true;
    };
  }, [selectedSku, selectedMetro, horizonDays, baselineLagDays, earlierByDays, marginRate]);

  const summary = simulation?.summary;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px', fontFamily: 'var(--font-serif)', letterSpacing: '-0.02em' }}>
            Early Signal Counterfactual
          </h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '1.02rem', margin: 0 }}>
            Simulation showing what would have happened if demand signals were caught earlier.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-primary)', fontWeight: 600 }}>
          <Sliders size={20} /> Scenario Inputs
        </div>
      </div>

      {error ? (
        <div className="metric-card" style={{ borderColor: 'var(--color-stockout-text)' }}>
          <div style={{ color: 'var(--color-stockout-text)', fontWeight: 600 }}>Simulation error</div>
          <div style={{ color: 'var(--color-text-secondary)', marginTop: '8px' }}>{error}</div>
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px', alignItems: 'stretch' }}>
        <div className="metric-card" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <h3 style={{ margin: 0, fontSize: '1.1rem', fontFamily: 'var(--font-serif)' }}>Model Controls</h3>

          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '6px' }}>SKU</div>
            <select
              value={selectedSku}
              onChange={(event) => setSelectedSku(event.target.value)}
              style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--color-surface-hover)', background: 'var(--color-surface-floating)', color: 'var(--color-text-primary)' }}
            >
              {skuOptions.map((option) => (
                <option key={option.sku_id} value={option.sku_id}>
                  {option.sku_id} - {option.product_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '6px' }}>Metro</div>
            <select
              value={selectedMetro}
              onChange={(event) => setSelectedMetro(event.target.value)}
              style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--color-surface-hover)', background: 'var(--color-surface-floating)', color: 'var(--color-text-primary)' }}
            >
              {metrosForSku.map((metro) => (
                <option key={metro} value={metro}>{metro}</option>
              ))}
            </select>
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.82rem' }}>
              <span>Current detection lag</span>
              <span>{baselineLagDays} days</span>
            </div>
            <input type="range" min="3" max="25" value={baselineLagDays} onChange={(e) => setBaselineLagDays(Number(e.target.value))} style={{ width: '100%', accentColor: 'var(--color-watch-text)' }} />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.82rem' }}>
              <span>Caught earlier by</span>
              <span>{earlierByDays} days</span>
            </div>
            <input
              type="range"
              min="1"
              max={Math.max(1, baselineLagDays - 1)}
              value={Math.min(earlierByDays, Math.max(1, baselineLagDays - 1))}
              onChange={(e) => setEarlierByDays(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--color-ok-text)' }}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.82rem' }}>
              <span>Simulation horizon</span>
              <span>{horizonDays} days</span>
            </div>
            <input type="range" min="30" max="120" step="5" value={horizonDays} onChange={(e) => setHorizonDays(Number(e.target.value))} style={{ width: '100%', accentColor: 'var(--color-primary)' }} />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.82rem' }}>
              <span>Margin assumption</span>
              <span>{Math.round(marginRate * 100)}%</span>
            </div>
            <input type="range" min="0.2" max="0.7" step="0.01" value={marginRate} onChange={(e) => setMarginRate(Number(e.target.value))} style={{ width: '100%', accentColor: 'var(--color-primary)' }} />
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(160px, 1fr))', gap: '12px' }}>
            <div className="metric-card">
              <div className="metric-title">Revenue Uplift</div>
              <div className="metric-value" style={{ fontSize: '1.35rem' }}>{formatMoney(summary?.revenue_uplift_usd)}</div>
              <div className="metric-trend" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><TrendingUp size={14} /> Caught earlier</div>
            </div>
            <div className="metric-card">
              <div className="metric-title">Profit Uplift</div>
              <div className="metric-value" style={{ fontSize: '1.35rem' }}>{formatMoney(summary?.profit_uplift_usd)}</div>
              <div className="metric-trend" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><DollarSign size={14} /> Net margin effect</div>
            </div>
            <div className="metric-card">
              <div className="metric-title">Units Saved</div>
              <div className="metric-value" style={{ fontSize: '1.35rem' }}>{Number(summary?.units_saved || 0).toLocaleString()}</div>
              <div className="metric-trend">Avoided lost sales</div>
            </div>
            <div className="metric-card">
              <div className="metric-title">Service Level Lift</div>
              <div className="metric-value" style={{ fontSize: '1.35rem' }}>{formatPct((summary?.early_service_level_pct || 0) - (summary?.baseline_service_level_pct || 0))}</div>
              <div className="metric-trend">Baseline vs earlier</div>
            </div>
          </div>

          <div className="metric-card" style={{ minHeight: '520px' }}>
            <h3 style={{ fontSize: '1.08rem', marginTop: 0, marginBottom: '14px' }}>Inventory and Profit Trajectory</h3>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.84rem', marginBottom: '12px' }}>
              Event date: {summary?.event_date || '-'} | Lead time: {summary?.lead_time_days || '-'}d | Replenishment: {Number(summary?.replenishment_units || 0).toLocaleString()} units
            </div>

            {loading ? (
              <div style={{ color: 'var(--color-text-secondary)' }}>Running simulation...</div>
            ) : (simulation?.points || []).length === 0 ? (
              <div style={{ color: 'var(--color-text-secondary)' }}>No simulation points available for this selection.</div>
            ) : (
              <ResponsiveContainer width="100%" height={440}>
                <LineChart data={simulation.points} margin={{ top: 12, right: 24, left: 8, bottom: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                  <XAxis dataKey="date" tickFormatter={formatDateLabel} tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }} axisLine={false} tickLine={false} minTickGap={24} />
                  <YAxis yAxisId="inv" tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis yAxisId="profit" orientation="right" tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-diffused)', backgroundColor: 'var(--color-surface-floating)' }}
                    labelFormatter={(label) => `Date: ${label}`}
                  />
                  <Legend wrapperStyle={{ paddingTop: '14px' }} />

                  <Line yAxisId="inv" type="monotone" dataKey="inventory_baseline" name="Inventory (current detection)" stroke="var(--color-stockout-text)" strokeWidth={2.4} dot={false} />
                  <Line yAxisId="inv" type="monotone" dataKey="inventory_early" name="Inventory (caught earlier)" stroke="var(--color-ok-text)" strokeWidth={2.4} dot={false} />
                  <Line yAxisId="profit" type="monotone" dataKey="cumulative_profit_baseline" name="Cumulative profit (current)" stroke="var(--color-watch-text)" strokeWidth={2.2} dot={false} />
                  <Line yAxisId="profit" type="monotone" dataKey="cumulative_profit_early" name="Cumulative profit (earlier)" stroke="var(--color-primary)" strokeWidth={2.2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
