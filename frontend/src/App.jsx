import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import SkuRiskOverview from './views/SkuRiskOverview';
import SignalTimeline from './views/SignalTimeline';
import BuyerBrief from './views/BuyerBrief';
import Simulation from './views/Simulation';
import { distributionCenters } from './data';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('overview');
  const [theme, setTheme] = useState('light');
  const [selectedDC, setSelectedDC] = useState('ALL');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const renderView = () => {
    switch (currentView) {
      case 'overview': return <SkuRiskOverview theme={theme} selectedDC={selectedDC} />;
      case 'timeline': return <SignalTimeline theme={theme} selectedDC={selectedDC} />;
      case 'brief': return <BuyerBrief theme={theme} selectedDC={selectedDC} />;
      case 'simulation': return <Simulation theme={theme} selectedDC={selectedDC} />;
      default: return <SkuRiskOverview theme={theme} selectedDC={selectedDC} />;
    }
  };

  return (
    <div className="app-layout">
      <Sidebar 
        currentView={currentView} 
        setCurrentView={setCurrentView} 
        theme={theme} 
        toggleTheme={toggleTheme}
        distributionCenters={distributionCenters}
        selectedDC={selectedDC}
        setSelectedDC={setSelectedDC}
      />
      <main className="main-content">
        <div className="scrollable-area">
          {renderView()}
        </div>
      </main>
    </div>
  );
}

export default App;
