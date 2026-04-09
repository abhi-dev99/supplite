export default function Simulation() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px', height: '100%' }}>
      <div>
        <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Simulation Mode</h1>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: '1rem', margin: 0 }}>
          Replaying scenario from Week -3 | Showing "What actually happened" vs "With System"
        </p>
      </div>

      <div style={{ display: 'flex', gap: '24px', flex: 1 }}>
        <div style={{
          flex: 1, backgroundColor: 'var(--color-surface-floating)', padding: '32px', borderRadius: '8px', 
          borderTop: '4px solid var(--color-stockout-text)', boxShadow: 'var(--shadow-diffused)'
        }}>
          <h3 style={{ fontSize: '1.25rem', marginBottom: '24px' }}>What Actually Happened</h3>
          <div style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
            <p><strong>Timeline:</strong> Week 0</p>
            <p><strong>Event:</strong> Sudden demand spike (412 units) drains local DC inventory immediately.</p>
            <p><strong>Response:</strong> Buyer initiates emergency re-order and out-of-market air freight shipments, eroding product margin by 64%.</p>
            <p><strong>Cost of delay:</strong> $42,000 lost in margin and unfulfilled orders.</p>
          </div>
        </div>

        <div style={{
          flex: 1, backgroundColor: 'var(--color-surface-floating)', padding: '32px', borderRadius: '8px', 
          borderTop: '4px solid var(--color-ok-text)', boxShadow: 'var(--shadow-diffused)'
        }}>
          <h3 style={{ fontSize: '1.25rem', marginBottom: '24px' }}>With Our System</h3>
          <div style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
            <p><strong>Timeline:</strong> Week -3</p>
            <p><strong>Event:</strong> Google Trends virality detected 3 weeks before demand materializes in sales data.</p>
            <p><strong>Response:</strong> Buyer receives brief and pre-positions 10-week lead time inventory using standard freight.</p>
            <p><strong>Value added:</strong> Margins protected, 100% fulfillment rate maintained across all 9 brands.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
