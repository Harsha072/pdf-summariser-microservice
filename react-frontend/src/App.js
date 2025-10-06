import React, { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header/Header';
import PaperDiscovery from './components/PaperDiscovery/PaperDiscovery';
import Notification from './components/Notification/Notification';
import { NotificationProvider } from './context/NotificationContext';

function App() {
  const [backendConnection, setBackendConnection] = useState('checking');

  useEffect(() => {
    // Check backend connection on startup
    checkBackendConnection();
  }, []);

  const checkBackendConnection = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/health');
      if (response.ok) {
        setBackendConnection('connected');
      } else {
        setBackendConnection('disconnected');
      }
    } catch (error) {
      console.error('Backend connection error:', error);
      setBackendConnection('disconnected');
    }
  };

  return (
    <NotificationProvider>
      <div className="app">
        <Header connectionStatus={backendConnection} />
        <main className="app-main">
          <PaperDiscovery />
        </main>
        <Notification />
      </div>
    </NotificationProvider>
  );
}

export default App;