import { LayoutDashboard, TrendingUp, FileText, SplitSquareHorizontal, Sun, Moon } from 'lucide-react';

export default function Sidebar({ currentView, setCurrentView, theme, toggleTheme }) {
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
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingTop: '24px',
        borderTop: '2px solid var(--color-background)'
      }}>
        <div style={{
          fontSize: '0.75rem',
          color: 'var(--color-text-secondary)'
        }}>
          <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '4px' }}>Data Freshness</div>
          <div>Signals updated: </div>
          <div>April 09, 2026</div>
        </div>
        
        <button 
          onClick={toggleTheme}
          style={{
            padding: '8px',
            borderRadius: '50%',
            backgroundColor: 'var(--color-surface-hover)',
            color: 'var(--color-text-primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
        </button>
      </div>
    </div>
  );
}
