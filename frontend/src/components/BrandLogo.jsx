export default function BrandLogo({ brand }) {
  if (brand === 'Pottery Barn') {
    return (
      <div style={{
        fontFamily: "'Times New Roman', Times, serif", // Mocking the PB thin serif
        fontWeight: 400,
        fontSize: '0.875rem',
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        lineHeight: 1
      }}>
        POTTERY BARN
      </div>
    );
  }
  if (brand === 'West Elm') {
    return (
      <div style={{
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif", // Mocking WE lowercase
        fontWeight: 300,
        fontSize: '0.875rem',
        letterSpacing: '0.05em',
        textTransform: 'lowercase'
      }}>
        west elm
      </div>
    );
  }
  if (brand === 'Williams Sonoma') {
    return (
      <div style={{
        fontFamily: "'Georgia', serif", // Mocking WS tight serif
        fontWeight: 700,
        fontSize: '0.85rem',
        letterSpacing: '0.02em',
        textTransform: 'uppercase'
      }}>
        WILLIAMS SONOMA
      </div>
    );
  }
  
  return <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{brand}</div>;
}
