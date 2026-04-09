export default function BuyerBrief() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px', maxWidth: '800px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Executive Buyer Brief</h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '1rem', margin: 0 }}>
            AI-generated summary for Week of April 09, 2026
          </p>
        </div>
        <button style={{
          backgroundColor: 'var(--color-primary)',
          color: 'var(--color-primary-on)',
          padding: '12px 24px',
          borderRadius: '4px',
          fontWeight: 600,
          fontSize: '0.875rem'
        }}>
          Export PDF
        </button>
      </div>

      <div style={{
        backgroundColor: 'var(--color-surface-floating)',
        padding: '48px',
        borderRadius: '8px',
        boxShadow: 'var(--shadow-diffused)',
        fontFamily: 'var(--font-serif)',
        lineHeight: 1.8,
        fontSize: '1.125rem'
      }}>
        <h2 style={{ color: 'var(--color-stockout-text)', fontSize: '1.25rem', marginBottom: '24px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Urgent — Action Required
        </h2>
        
        <p style={{ marginBottom: '12px' }}><strong>1. PB-BLANKET-42 (Pottery Barn Throw Blanket, Cognac)</strong></p>
        <ul style={{ marginBottom: '24px', color: 'var(--color-text-secondary)', fontSize: '1rem', fontFamily: 'var(--font-sans)' }}>
          <li>Current stock: 6,200 units | Lead time: 10 weeks | Days of supply: 34 days</li>
          <li><strong>SIGNAL:</strong> Search volume up 840% in 7 days (social virality detected)</li>
          <li><strong>FORECAST:</strong> 18,400 units demand by Dec 15 — 12,200 unit shortfall</li>
          <li><strong>ACTION:</strong> Expedite supplementary order from alternate vendor. Consider air freight for 3,000 units.</li>
        </ul>

        <div style={{ height: '1px', backgroundColor: 'var(--color-surface-hover)', margin: '40px 0' }} />

        <h2 style={{ color: 'var(--color-overstock-text)', fontSize: '1.25rem', marginBottom: '24px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Overstock Warning
        </h2>

        <p style={{ marginBottom: '12px' }}><strong>2. PB-PILLOW-71 (Decorative Pillow, Sage)</strong></p>
        <ul style={{ marginBottom: '24px', color: 'var(--color-text-secondary)', fontSize: '1rem', fontFamily: 'var(--font-sans)' }}>
          <li>Stock: 4,200 units | Selling rate: 47/week | Days of supply: 89 days</li>
          <li><strong>SIGNAL:</strong> Search declining 23% over 8 weeks</li>
          <li><strong>ACTION:</strong> Consider promotion or markdown trigger. Do not reorder.</li>
        </ul>
      </div>
    </div>
  );
}
