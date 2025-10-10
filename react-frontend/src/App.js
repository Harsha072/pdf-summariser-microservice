import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import Header from './components/Header/Header';
import PaperDiscovery from './components/PaperDiscovery/PaperDiscovery';
import PaperDetails from './components/PaperDetails/PaperDetails';
import Notification from './components/Notification/Notification';
import { NotificationProvider } from './context/NotificationContext';
import { createSession, getCurrentSessionId } from './services/api';

function App() {
  const [backendConnection, setBackendConnection] = useState('checking');

  useEffect(() => {
    // Initialize session and check backend connection on startup
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      // Initialize session if not exists
      let sessionId = getCurrentSessionId();
      if (!sessionId) {
        sessionId = await createSession();
        console.log('Created new session:', sessionId);
      } else {
        console.log('Using existing session:', sessionId);
      }
      
      // Check backend connection
      await checkBackendConnection();
    } catch (error) {
      console.error('App initialization error:', error);
      setBackendConnection('disconnected');
    }
  };

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
    <Router>
      <NotificationProvider>
        <div className="app">
          <Header connectionStatus={backendConnection} />
          <main className="app-main">
            <Routes>
              <Route path="/" element={<PaperDiscovery />} />
              <Route path="/paper-details/:paperId" element={<PaperDetails />} />
            </Routes>
          </main>
          <Notification />
        </div>
      </NotificationProvider>
    </Router>
  );
}

export default App;