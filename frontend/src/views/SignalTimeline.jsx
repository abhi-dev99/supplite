import { useEffect, useMemo, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { fetchSignalTimeline, fetchSignalTimelineOptions } from '../api/signalTimelineApi';

function formatDelta(value) {
  const num = Number(value || 0);
  const sign = num > 0 ? '+' : '';
  return `${sign}${num.toFixed(2)}`;
}

function formatDateLabel(value) {
  const text = String(value || '');
  if (text.length >= 10) {
    return text.slice(5);
  }
  return text;
}

export default function SignalTimeline({ selectedSku, setSelectedSku }) {
  const [skuOptions, setSkuOptions] = useState([]);
  const [periodOptions, setPeriodOptions] = useState([14, 30, 60, 90, 180]);
  const [periodDays, setPeriodDays] = useState(30);
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function loadOptions() {
      try {
        const payload = await fetchSignalTimelineOptions();
        if (cancelled) {
          return;
        }
        const options = payload.sku_options || [];
        setSkuOptions(options);
        if (Array.isArray(payload.period_options) && payload.period_options.length > 0) {
          setPeriodOptions(payload.period_options);
          if (!payload.period_options.includes(periodDays)) {
            setPeriodDays(payload.period_options[0]);
          }
        }

        const firstSku = options[0]?.sku_id || '';
        if (typeof setSelectedSku === 'function') {
          if (selectedSku && options.some((option) => option.sku_id === selectedSku)) {
            setSelectedSku(selectedSku);
          } else if (firstSku) {
            setSelectedSku(firstSku);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load timeline options');
        }
      }
    }

    loadOptions();
    return () => {
      cancelled = true;
    };
  }, [setSelectedSku, selectedSku]);

  useEffect(() => {
    if (!selectedSku) {
      return;
    }

    let cancelled = false;
    async function loadTimeline() {
      setLoading(true);
      try {
        const payload = await fetchSignalTimeline({ skuId: selectedSku, periodDays });
        if (!cancelled) {
          setTimeline(payload);
          setError('');
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load signal timeline');
          setTimeline(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadTimeline();
    return () => {
      cancelled = true;
    };
  }, [selectedSku, periodDays]);

  const activeSku = useMemo(
    () => skuOptions.find((option) => option.sku_id === selectedSku) || null,
    [skuOptions, selectedSku],
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Signal Timeline</h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '1rem', margin: 0 }}>
            Compare sales velocity vs search velocity trends for each SKU over selectable periods.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <select
            value={selectedSku || ''}
            onChange={(event) => {
              if (typeof setSelectedSku === 'function') {
                setSelectedSku(event.target.value);
              }
            }}
            style={{
              padding: '10px 12px',
              borderRadius: '8px',
              border: '1px solid var(--color-surface-hover)',
              background: 'var(--color-surface-floating)',
              color: 'var(--color-text-primary)',
              minWidth: '230px',
            }}
          >
            {skuOptions.map((option) => (
              <option key={option.sku_id} value={option.sku_id}>
                {option.sku_id} - {option.product_name}
              </option>
            ))}
          </select>

          <select
            value={periodDays}
            onChange={(event) => setPeriodDays(Number(event.target.value))}
            style={{
              padding: '10px 12px',
              borderRadius: '8px',
              border: '1px solid var(--color-surface-hover)',
              background: 'var(--color-surface-floating)',
              color: 'var(--color-text-primary)',
              minWidth: '140px',
            }}
          >
            {periodOptions.map((option) => (
              <option key={option} value={option}>{option} days</option>
            ))}
          </select>
        </div>
      </div>

      {error ? (
        <div className="metric-card" style={{ borderColor: 'var(--color-stockout-text)' }}>
          <div style={{ color: 'var(--color-stockout-text)', fontWeight: 600 }}>Timeline error</div>
          <div style={{ color: 'var(--color-text-secondary)', marginTop: '8px' }}>{error}</div>
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
        <div className="metric-card">
          <div className="metric-title">SKU</div>
          <div className="metric-value" style={{ fontSize: '1.25rem' }}>{timeline?.sku_id || activeSku?.sku_id || '-'}</div>
          <div className="metric-trend">{timeline?.product_name || activeSku?.product_name || 'Loading...'}</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Category</div>
          <div className="metric-value" style={{ fontSize: '1.25rem' }}>{timeline?.category || activeSku?.category || '-'}</div>
          <div className="metric-trend">Period: {timeline?.period_days || periodDays} days</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Sales Delta</div>
          <div className="metric-value" style={{ fontSize: '1.25rem' }}>{formatDelta(timeline?.summary?.sales_delta)}</div>
          <div className="metric-trend">7D sales velocity change</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Search Delta</div>
          <div className="metric-value" style={{ fontSize: '1.25rem' }}>{formatDelta(timeline?.summary?.search_delta)}</div>
          <div className="metric-trend">7D search velocity change</div>
        </div>
      </div>

      <div
        style={{
          minHeight: '520px',
          backgroundColor: 'var(--color-surface-floating)',
          padding: '24px',
          borderRadius: '12px',
          boxShadow: 'var(--shadow-diffused)',
          border: '1px solid var(--color-surface-hover)',
        }}
      >
        {loading ? (
          <div style={{ color: 'var(--color-text-secondary)' }}>Loading timeline...</div>
        ) : (timeline?.points || []).length === 0 ? (
          <div style={{ color: 'var(--color-text-secondary)' }}>No timeline points found for this SKU and period.</div>
        ) : (
          <ResponsiveContainer width="100%" height={470}>
            <LineChart data={timeline.points} margin={{ top: 20, right: 30, left: 10, bottom: 30 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDateLabel}
                tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                minTickGap={22}
              />
              <YAxis yAxisId="left" tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-diffused)', backgroundColor: 'var(--color-surface-floating)' }}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Legend wrapperStyle={{ paddingTop: '16px' }} />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="sales_velocity_7d"
                name="Sales velocity (7d %)"
                stroke="var(--color-stockout-text)"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5 }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="search_velocity_7d"
                name="Search velocity (7d %)"
                stroke="var(--color-watch-text)"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
