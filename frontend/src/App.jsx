import { useState } from 'react';
import Sidebar from './components/Sidebar';
import SkuRiskOverview from './views/SkuRiskOverview';
import SignalTimeline from './views/SignalTimeline';
import BuyerBrief from './views/BuyerBrief';
import Simulation from './views/Simulation';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('overview');

  const renderView = () => {
    switch (currentView) {
      case 'overview': return <SkuRiskOverview />;
      case 'timeline': return <SignalTimeline />;
      case 'brief': return <BuyerBrief />;
      case 'simulation': return <Simulation />;
      default: return <SkuRiskOverview />;
    }
  };

  return (
    <div className="app-layout">
      <Sidebar currentView={currentView} setCurrentView={setCurrentView} />
      <main className="main-content">
        <div className="scrollable-area">
          {renderView()}
        </div>
      </main>
    </div>
  );
}

export default App;
