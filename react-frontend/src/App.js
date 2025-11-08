import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import Header from './components/Header/Header';
import HomePage from './pages/HomePage';
import PaperDiscovery from './components/PaperDiscovery/PaperDiscovery';
import PaperDetails from './components/PaperDetails/PaperDetails';
import SideNavigation from './components/SideNavigation/SideNavigation';
import SearchHistoryPage from './pages/SearchHistory';
import SavedPapers from './pages/SavedPapers';
import HelpGuide from './pages/HelpGuide';
import UserProfile from './pages/UserProfile';
import SimplePaperRelationshipsPage from './pages/SimplePaperRelationshipsPage';
import Notification from './components/Notification/Notification';
import { NotificationProvider } from './context/NotificationContext';
import { AuthProvider } from './context/AuthContext';
import { createSession, getCurrentSessionId } from './services/api';

// Use environment variable for API URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function App() {
  const [backendConnection, setBackendConnection] = useState('checking');
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  useEffect(() => {
    // Initialize session and check backend connection on startup
    initializeApp();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const initializeApp = async () => {
    try {
      // Initialize session if not exists
      let sessionId = getCurrentSessionId();
      if (!sessionId) {
        sessionId = await createSession();
        console.log('Created a new session:', sessionId);
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
      const response = await fetch(`${API_BASE_URL}/api/health`);
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

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  const closeMenu = () => {
    setIsMenuOpen(false);
  };

  return (
    <Router>
      <AuthProvider>
        <NotificationProvider>
          <div className="app">
            <Header 
              connectionStatus={backendConnection} 
              onMenuToggle={toggleMenu}
              isMenuOpen={isMenuOpen}
            />
            <SideNavigation 
              isOpen={isMenuOpen}
              onClose={closeMenu}
            />
            <main className="app-main">
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/search" element={<PaperDiscovery />} />
                <Route path="/paper-details/:paperId" element={<PaperDetails />} />
                <Route path="/paper-relationships" element={<SimplePaperRelationshipsPage />} />
                <Route path="/history" element={<SearchHistoryPage />} />
                <Route path="/saved" element={<SavedPapers />} />
                <Route path="/help" element={<HelpGuide />} />
                <Route path="/profile" element={<UserProfile />} />
              </Routes>
            </main>
            <Notification />
          </div>
        </NotificationProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;