import React, { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header/Header';
import PDFPanel from './components/PDFPanel/PDFPanel';
import ControlPanel from './components/ControlPanel/ControlPanel';
import Notification from './components/Notification/Notification';
import { DocumentProvider } from './context/DocumentContext';
import { NotificationProvider } from './context/NotificationContext';

function App() {
  const [backendConnection, setBackendConnection] = useState('checking');

  useEffect(() => {
    // Check backend connection on startup
    checkBackendConnection();
  }, []);

  const checkBackendConnection = async () => {
    try {
      const response = await fetch('/api/health');
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
      <DocumentProvider>
        <div className="app">
          <Header connectionStatus={backendConnection} />
          <main className="app-main">
            <div className="app-container">
              <PDFPanel />
              <ControlPanel />
            </div>
          </main>
          <Notification />
        </div>
      </DocumentProvider>
    </NotificationProvider>
  );
}

export default App;