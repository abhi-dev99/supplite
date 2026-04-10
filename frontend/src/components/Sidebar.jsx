import { LayoutDashboard, TrendingUp, FileText, SplitSquareHorizontal, Sun, Moon, MapPin } from 'lucide-react';
import { useMemo } from 'react';

export default function Sidebar({ currentView, setCurrentView, theme, toggleTheme, distributionCenters, selectedDC, setSelectedDC }) {
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
      <h2 style={{ fontSize: '1.25rem', marginBottom: '32px', color: 'var(--color-text-primary)' }}>
        Demand Intelligence
      </h2>

      <div style={{ marginBottom: '32px' }}>
        <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
           <MapPin size={14} /> Active Node
        </label>
        <select 
          value={selectedDC} 
          onChange={(e) => setSelectedDC(e.target.value)}
          style={{
            width: '100%',
            padding: '10px 12px',
            borderRadius: '6px',
            backgroundColor: 'var(--color-surface-floating)',
            color: 'var(--color-text-primary)',
            border: '1px solid var(--color-border)',
            fontSize: '0.875rem',
            fontFamily: 'var(--font-sans)',
            cursor: 'pointer',
            outline: 'none'
          }}
        >
          <option value="ALL">North America (Global View)</option>
          {distributionCenters && distributionCenters
            .filter(dc => ['City of Industry DC', 'Braselton DC', 'Dallas DC', 'Litchfield Park DC', 'Oakland, CA', 'Lakeland, FL', 'Denver, CO', 'South Brunswick DC'].includes(dc.name))
            .map(dc => (
            <option key={dc.name} value={dc.name}>{dc.name} ({dc.type})</option>
          ))}
        </select>
      </div>
      
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
