import { useEffect, useState } from 'react';
import { Search, Maximize2, X, BookOpenText } from 'lucide-react';
import { mockSkus } from '../data';
import SciFiMap from '../components/SciFiMap';
import BrandLogo from '../components/BrandLogo';
import { fetchSkuBios } from '../api/skuBioApi';

export default function SkuRiskOverview({ theme, selectedDC, setCurrentView, setSelectedTimelineSku, setSelectedCatalogSku }) {
  const [activeTab, setActiveTab] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isMapExpanded, setIsMapExpanded] = useState(false);
  const [isMapHovered, setIsMapHovered] = useState(false);
  const [hoverTimer, setHoverTimer] = useState(null);
  const [hubMetrics, setHubMetrics] = useState({
    loading: true,
    capitalExposure: 0,
    trajectoryShifts: 0,
    recordCount: 0,
    source: 'generated-data',
  });

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

  useEffect(() => {
    let cancelled = false;

    async function loadHubMetrics() {
      setHubMetrics((prev) => ({ ...prev, loading: true }));
      try {
        const payload = await fetchSkuBios({ dc: selectedDC || 'ALL', limit: 2500 });
        if (cancelled) {
          return;
        }

        const records = Array.isArray(payload?.records) ? payload.records : [];
        const capitalExposure = records.reduce((sum, row) => {
          const stock = Number(row.stock_on_hand || 0);
          const onOrder = Number(row.on_order || 0);
          const price = Number(row.price || 0);
          return sum + ((stock + onOrder) * price);
        }, 0);

        const trajectoryShifts = records.filter((row) => {
          const sales7d = Math.abs(Number(row.sales_velocity_7d || 0));
          const search7d = Math.abs(Number(row.search_velocity_7d || 0));
          const trend = String(row.trend_label || '').toLowerCase();
          const surgeFlag = String(row.surge_flag || '').toUpperCase();
          return (
            trend === 'surging'
            || trend === 'accelerating'
            || trend === 'cooling'
            || surgeFlag === 'VIRAL'
            || surgeFlag === 'SPIKE'
            || sales7d >= 15
            || search7d >= 20
          );
        }).length;

        setHubMetrics({
          loading: false,
          capitalExposure,
          trajectoryShifts,
          recordCount: records.length,
          source: 'generated-data',
        });
      } catch {
        if (cancelled) {
          return;
        }
        const fallbackCapital = mockSkus.reduce((sum, sku) => sum + ((Number(sku.stock || 0) + Number(sku.onOrder || 0)) * Number(sku.price || 0)), 0);
        const fallbackShifts = mockSkus.filter((sku) => sku.anomalyFlag).length;
        setHubMetrics({
          loading: false,
          capitalExposure: fallbackCapital,
          trajectoryShifts: fallbackShifts,
          recordCount: mockSkus.length,
          source: 'frontend-fallback',
        });
      }
    }

    loadHubMetrics();
    return () => {
      cancelled = true;
    };
  }, [selectedDC]);

  const formatCompactCurrency = (value) => {
    const num = Number(value || 0);
    if (Math.abs(num) >= 1_000_000_000) {
      return `$${(num / 1_000_000_000).toFixed(1)}B`;
    }
    if (Math.abs(num) >= 1_000_000) {
      return `$${(num / 1_000_000).toFixed(1)}M`;
    }
    if (Math.abs(num) >= 1_000) {
      return `$${(num / 1_000).toFixed(1)}K`;
    }
    return `$${num.toFixed(0)}`;
  };

  const escapeMd = (value) => String(value ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');

  const markdownTable = (headers, rows) => {
    const headerRow = `| ${headers.join(' | ')} |`;
    const dividerRow = `| ${headers.map(() => '---').join(' | ')} |`;
    const body = rows.map((row) => `| ${row.map((cell) => escapeMd(cell)).join(' | ')} |`).join('\n');
    return [headerRow, dividerRow, body].filter(Boolean).join('\n');
  };

  const downloadFile = (fileName, content, mimeType) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  const handleExportReport = () => {
    const riskCounts = {
      STOCKOUT_RISK: sortedSkus.filter((item) => item.riskLevel === 'STOCKOUT_RISK').length,
      OVERSTOCK_RISK: sortedSkus.filter((item) => item.riskLevel === 'OVERSTOCK_RISK').length,
      WATCH: sortedSkus.filter((item) => item.riskLevel === 'WATCH').length,
      OK: sortedSkus.filter((item) => item.riskLevel === 'OK').length,
    };

    const totalInventoryValue = sortedSkus.reduce((sum, item) => sum + ((item.stock + item.onOrder) * (item.price || 0)), 0);
    const avgDaysOfSupply = sortedSkus.length
      ? (sortedSkus.reduce((sum, item) => sum + Number(item.daysOfSupply || 0), 0) / sortedSkus.length).toFixed(1)
      : '0.0';

    const topCritical = [...sortedSkus]
      .filter((item) => item.riskLevel === 'STOCKOUT_RISK')
      .sort((a, b) => (Number(b.mlForecast60d || 0) - Number(a.mlForecast60d || 0)))
      .slice(0, 10);

    const kpiTable = markdownTable(
      ['Metric', 'Value'],
      [
        ['Node Scope', selectedDC],
        ['Active Portfolio Filter', activeTab],
        ['Search Filter', searchQuery || 'None'],
        ['Rows In Report', String(sortedSkus.length)],
        ['Critical Shortages Predicted', String(riskCounts.STOCKOUT_RISK)],
        ['Trajectory Shifts (Anomalies)', String(sortedSkus.filter((s) => s.anomalyFlag).length)],
        ['Estimated Inventory Value (On Hand + On Order)', `$${Math.round(totalInventoryValue).toLocaleString()}`],
        ['Average Days of Supply', `${avgDaysOfSupply} days`],
      ],
    );

    const riskTable = markdownTable(
      ['Risk Bucket', 'Count'],
      [
        ['STOCKOUT_RISK', String(riskCounts.STOCKOUT_RISK)],
        ['OVERSTOCK_RISK', String(riskCounts.OVERSTOCK_RISK)],
        ['WATCH', String(riskCounts.WATCH)],
        ['OK', String(riskCounts.OK)],
      ],
    );

    const criticalTable = markdownTable(
      ['SKU', 'Product', 'Brand', 'Category', 'Stock+Pipeline', 'DOS', 'Lead Time', 'Forecast 60D', 'Signal', 'Action'],
      topCritical.map((item) => [
        item.id,
        item.name,
        item.brand,
        item.category,
        (item.stock + item.onOrder).toLocaleString(),
        String(item.daysOfSupply),
        String(item.leadTimeDays),
        (item.mlForecast60d || 0).toLocaleString(),
        item.signal,
        item.action,
      ]),
    );

    const fullTable = markdownTable(
      ['SKU', 'Product', 'Brand', 'Category', 'Risk', 'Stock', 'On Order', 'DOS', 'Lead Time', 'Forecast 60D', 'Price', 'Signal', 'Action', 'AI Reasoning'],
      sortedSkus.map((item) => [
        item.id,
        item.name,
        item.brand,
        item.category,
        item.riskLevel,
        String(item.stock),
        String(item.onOrder),
        String(item.daysOfSupply),
        String(item.leadTimeDays),
        String(item.mlForecast60d || 0),
        String(item.price || 0),
        item.signal || '',
        item.action || '',
        item.mlReasoning || '',
      ]),
    );

    const generatedAt = new Date().toISOString();
    const report = [
      '# Intelligence Hub Report',
      '',
      `- Generated At: ${generatedAt}`,
      `- Node Scope: ${selectedDC}`,
      `- Portfolio Filter: ${activeTab}`,
      `- Search Filter: ${searchQuery || 'None'}`,
      `- Sort: ${sortConfig.key ? `${sortConfig.key} (${sortConfig.direction})` : 'Default'}`,
      '',
      '## KPI Snapshot',
      '',
      kpiTable,
      '',
      '## Risk Distribution',
      '',
      riskTable,
      '',
      '## Top Critical SKUs (Stockout Risk)',
      '',
      criticalTable,
      '',
      '## Full SKU Intelligence Table',
      '',
      fullTable,
      '',
      '## Methodology Notes',
      '',
      '- Report is exported from live Intelligence Hub state (current filters, search, and sorting).',
      '- Values are sourced from generated SKU dataset and include signal/action/reasoning text for every row.',
      '- This export is data-first and audit-friendly (not print/screenshot output).',
      '',
    ].join('\n');

    const fileScope = String(selectedDC || 'ALL').replace(/\s+/g, '_').toLowerCase();
    const fileStamp = generatedAt.replace(/[:.]/g, '-');
    downloadFile(`intelligence_hub_report_${fileScope}_${fileStamp}.md`, report, 'text/markdown;charset=utf-8');
  };

  const filteredSkus = mockSkus.filter(sku => {
    const text = searchQuery.trim().toLowerCase();
    const matchesSearch = !text
      || sku.id.toLowerCase().includes(text)
      || sku.name.toLowerCase().includes(text)
      || sku.brand.toLowerCase().includes(text)
      || sku.category.toLowerCase().includes(text)
      || (sku.signal || '').toLowerCase().includes(text);

    if (!matchesSearch) {
      return false;
    }
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
            <button className="export-report-btn" onClick={handleExportReport} disabled={sortedSkus.length === 0}>Export Report</button>
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
                   {hubMetrics.loading ? '...' : formatCompactCurrency(hubMetrics.capitalExposure)}
                 </div>
                 <div className="metric-trend" style={{ color: 'var(--color-text-secondary)' }}>
                   {hubMetrics.loading ? 'Computing from generated data...' : `${hubMetrics.recordCount.toLocaleString()} records in scope`}
                 </div>
              </div>

              <div className="metric-card glass-panel" style={{ flex: 1, padding: '24px' }}>
                 <div className="metric-title" style={{ fontSize: '0.65rem' }}>Trajectory Shifts</div>
                 <div className="metric-value" style={{ fontSize: '1.75rem' }}>{hubMetrics.loading ? '...' : hubMetrics.trajectoryShifts}</div>
                 <div className="metric-trend" style={{ color: 'var(--color-text-secondary)' }}>
                   {hubMetrics.source === 'frontend-fallback' ? 'Fallback anomaly rule (frontend data)' : 'Signal regime shifts detected'}
                 </div>
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
              <input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} type="text" placeholder="Search catalog..." style={{ border: 'none', background: 'transparent', outline: 'none', color: 'var(--color-text-primary)', fontSize: '0.875rem' }} />
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
              <div>AI Reasoning</div>
            </div>

            {/* List Rows */}
            {sortedSkus.map((sku, idx) => (
              <div
                key={sku.id}
                className="data-row glass-panel"
                style={{ animationDelay: `${idx * 0.05}s`, cursor: 'pointer' }}
                onClick={() => {
                  if (typeof setSelectedTimelineSku === 'function') {
                    setSelectedTimelineSku(sku.id);
                  }
                  if (typeof setCurrentView === 'function') {
                    setCurrentView('timeline');
                  }
                }}
              >
                
                {/* Product Col */}
                <div className="hub-product-cell">
                   <div style={{ opacity: 0.8 }}><BrandLogo brand={sku.brand} /></div>
                   <div>
                     <div className="hub-product-name" style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--color-text-primary)' }}>{sku.name}</div>
                     <div className="text-sub">{sku.id} • {sku.category}</div>
                   </div>
                   <button
                     onClick={(event) => {
                       event.stopPropagation();
                       if (typeof setSelectedCatalogSku === 'function') {
                         setSelectedCatalogSku(sku.id);
                       }
                       if (typeof setCurrentView === 'function') {
                         setCurrentView('catalog');
                       }
                     }}
                     style={{
                       marginLeft: '8px',
                       border: '1px solid var(--color-surface-hover)',
                       background: 'var(--color-surface-floating)',
                       color: 'var(--color-text-secondary)',
                       borderRadius: '6px',
                       padding: '5px 8px',
                       display: 'inline-flex',
                       alignItems: 'center',
                       gap: '6px',
                       fontSize: '0.7rem',
                       cursor: 'pointer',
                     }}
                     title="Open SKU Atlas profile"
                   >
                     <BookOpenText size={12} /> Atlas
                   </button>
                </div>

                {/* Stock Col */}
                <div className="hub-metric-cell">
                  <div className="hub-metric-value" style={{ fontWeight: 600, fontSize: '1rem' }}>
                    {selectedDC === 'ALL' ? (sku.stock + sku.onOrder).toLocaleString() : Math.floor((sku.stock + sku.onOrder) / 11).toLocaleString()}
                  </div>
                  <div className="text-sub">Physical + Pipeline</div>
                </div>

                {/* Runway Col */}
                <div className="hub-metric-cell" style={{ paddingRight: '24px' }}>
                  <div className="hub-metric-value" style={{ fontWeight: 600 }}>{sku.daysOfSupply} Days</div>
                  <div className="runway-bar-bg">
                    <div className="runway-bar-fill" style={{ 
                      width: `${Math.min((sku.daysOfSupply / 120) * 100, 100)}%`,
                      background: sku.daysOfSupply < sku.leadTimeDays ? 'var(--color-stockout-text)' : 'var(--color-ok-text)'
                    }}></div>
                  </div>
                </div>

                {/* Forecast Col */}
                <div className="hub-metric-cell">
                   <div className="hub-metric-value" style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
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
                <div className="hub-reasoning" style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
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
