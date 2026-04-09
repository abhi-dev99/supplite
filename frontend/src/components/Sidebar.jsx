import { LayoutDashboard, TrendingUp, FileText, SplitSquareHorizontal } from 'lucide-react';

export default function Sidebar({ currentView, setCurrentView }) {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'timeline', label: 'Signal Timeline', icon: TrendingUp },
    { id: 'brief', label: 'Buyer Brief', icon: FileText },
    { id: 'simulation', label: 'Simulation', icon: SplitSquareHorizontal },
  ];

  return (
    <div style={{
      width: '260px',
      backgroundColor: 'var(--color-surface)',
      borderRight: '1px solid var(--color-background)',
      display: 'flex',
      flexDirection: 'column',
      padding: '32px 24px',
      height: '100%'
    }}>
      <h2 style={{ fontSize: '1.25rem', marginBottom: '48px', color: 'var(--color-text-primary)' }}>
        Demand Intelligence
      </h2>
      
      <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {navItems.map(item => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setCurrentView(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 16px',
                borderRadius: '8px',
                backgroundColor: isActive ? 'var(--color-surface-floating)' : 'transparent',
                color: isActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                fontWeight: isActive ? 600 : 500,
                boxShadow: isActive ? 'var(--shadow-diffused)' : 'none',
                transition: 'all 0.2s ease',
                textAlign: 'left'
              }}
            >
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div style={{
        marginTop: 'auto',
        paddingTop: '24px',
        borderTop: '2px solid var(--color-background)',
        fontSize: '0.75rem',
        color: 'var(--color-text-secondary)'
      }}>
        <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '4px' }}>Data Freshness</div>
        <div>Signals last updated:</div>
        <div>April 09, 2026 09:00 AM</div>
      </div>
    </div>
  );
}
