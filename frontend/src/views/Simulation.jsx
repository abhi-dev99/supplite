import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea } from 'recharts';
import { Sliders, ShieldCheck, AlertTriangle } from 'lucide-react';

export default function Simulation() {
  const [mitigationApplied, setMitigationApplied] = useState(false);
  const [freightSpeed, setFreightSpeed] = useState(30);

  // Mock forecast data showing stock trajectory
  const generateData = () => {
    let stock = 6200;
    const data = [];
    for (let week = 1; week <= 12; week++) {
      // High demand drain
      stock -= 800 + Math.random() * 200;
      
      // If mitigation applied, inject new supply at week 4
      if (mitigationApplied && week === 4) {
        stock += 5000;
      }
      
      data.push({
        week: `Wk ${week}`,
        stock: Math.max(0, stock)
      });
    }
    return data;
  };

  const currentData = generateData();
  const willStockout = currentData.some(d => d.stock === 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px', fontFamily: 'var(--font-serif)', letterSpacing: '-0.02em' }}>
            Scenario Simulator
          </h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '1.05rem', margin: 0 }}>
            Testing "What-If" impact for PB-BLANKET-42 based on social virality signals.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-primary)', fontWeight: 600 }}>
          <Sliders size={20} /> Parameters
        </div>
      </div>

      <div style={{ display: 'flex', gap: '24px', flex: 1 }}>
        {/* Controls Sidebar */}
        <div className="metric-card" style={{ width: '300px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <h3 style={{ fontSize: '1.125rem', fontFamily: 'var(--font-serif)', margin: 0 }}>Model Variables</h3>
          
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.875rem', fontWeight: 500 }}>
              <span>Expedite Freight (Days)</span>
              <span>{freightSpeed}d</span>
            </div>
            <input 
              type="range" 
              min="10" 
              max="90" 
              value={freightSpeed} 
              onChange={(e) => setFreightSpeed(e.target.value)}
              style={{ width: '100%', accentColor: 'var(--color-text-primary)' }}
            />
          </div>

          <div>
            <div style={{ fontSize: '0.875rem', fontWeight: 500, marginBottom: '8px' }}>AI Recommended Action</div>
            <div style={{ 
              backgroundColor: 'var(--color-background)', 
              padding: '12px', 
              borderRadius: '6px',
              fontSize: '0.875rem',
              color: 'var(--color-text-secondary)',
              lineHeight: 1.5,
              border: '1px solid var(--border-ghost, rgba(0,0,0,0.05))'
            }}>
              Pre-position 5,000 units via ocean freight immediately to circumvent domestic carrier bottlenecks.
            </div>
          </div>

          <button 
            onClick={() => setMitigationApplied(!mitigationApplied)}
            style={{
              backgroundColor: mitigationApplied ? 'var(--color-surface-hover)' : 'var(--color-primary)',
              color: mitigationApplied ? 'var(--color-text-primary)' : 'var(--color-primary-on)',
              padding: '16px',
              borderRadius: '8px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'all 0.2s',
              border: mitigationApplied ? '1px solid var(--border-ghost, rgba(0,0,0,0.1))' : 'none'
            }}
          >
            {mitigationApplied ? 'Remove Mitigation' : 'Apply Recommended Mitigation'}
          </button>
          
          <div style={{ marginTop: 'auto', paddingTop: '24px', borderTop: '1px solid var(--color-background)' }}>
             <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '8px' }}>Projected Outcomes</div>
             <div style={{ display: 'flex', gap: '8px', alignItems: 'center', color: willStockout ? 'var(--color-stockout-text)' : 'var(--color-ok-text)', fontWeight: 600 }}>
               {willStockout ? <AlertTriangle size={16} /> : <ShieldCheck size={16} />}
               {willStockout ? '-$42,000 Margin Loss' : '100% Demand Captured'}
             </div>
          </div>
        </div>

        {/* Chart View */}
        <div className="metric-card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: '1.125rem', fontFamily: 'var(--font-serif)', margin: '0 0 24px 0' }}>12-Week Inventory Projection</h3>
          
          <div style={{ flex: 1 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={currentData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                <XAxis dataKey="week" tick={{fill: 'var(--color-text-secondary)', fontSize: 12}} axisLine={false} tickLine={false} />
                <YAxis tick={{fill: 'var(--color-text-secondary)', fontSize: 12}} axisLine={false} tickLine={false} />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-diffused)', backgroundColor: 'var(--color-surface-floating)' }}
                />
                
                {willStockout && (
                  <ReferenceArea y1={0} y2={100} fill="var(--color-stockout-bg)" fillOpacity={0.5} />
                )}

                <Line 
                  type="monotone" 
                  dataKey="stock" 
                  name="Inventory Units" 
                  stroke="var(--color-text-primary)" 
                  strokeWidth={3} 
                  dot={{ r: 4, fill: 'var(--color-surface-floating)' }} 
                  activeDot={{ r: 8 }} 
                  animationDuration={500}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
