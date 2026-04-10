import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { mockChartData } from '../data';

export default function SignalTimeline() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px', height: '100%' }}>
      <div>
        <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Signal Timeline</h1>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: '1rem', margin: 0 }}>
          Multi-axis view for PB-BLANKET-42 (Virality Detected)
        </p>
      </div>

      <div style={{
        flex: 1,
        backgroundColor: 'var(--color-surface-floating)',
        padding: '32px',
        borderRadius: '8px',
        boxShadow: 'var(--shadow-diffused)'
      }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={mockChartData} margin={{ top: 20, right: 50, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
            <XAxis dataKey="name" tick={{fill: '#474747', fontSize: 12}} axisLine={false} tickLine={false} />
            <YAxis yAxisId="left" tick={{fill: '#1a1c1d', fontSize: 12}} axisLine={false} tickLine={false} />
            <YAxis yAxisId="right" orientation="right" tick={{fill: '#005ac2', fontSize: 12}} axisLine={false} tickLine={false} />
            <Tooltip 
              contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-diffused)' }}
            />
            <Legend wrapperStyle={{ paddingTop: '20px' }} />
            
            <ReferenceLine yAxisId="left" x="Current" stroke="var(--color-stockout-text)" strokeDasharray="3 3" label="Signal Event" />
            
            <Line yAxisId="left" type="monotone" dataKey="sales" name="Sales History" stroke="#1a1c1d" strokeWidth={3} dot={{r: 4}} activeDot={{r: 8}} />
            <Line yAxisId="right" type="monotone" dataKey="search" name="Google Trends Index" stroke="#ba1a1a" strokeWidth={3} dot={false} />
            <Line yAxisId="right" type="monotone" dataKey="permits" name="US Census Permits" stroke="#005ac2" strokeWidth={3} dot={false} strokeDasharray="5 5" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
