import React, { createContext, useContext, useEffect, useState } from 'react';
import { 
  signInWithPopup, 
  signOut, 
  onAuthStateChanged,
  signInAnonymously 
} from 'firebase/auth';
import { auth, googleProvider, githubProvider } from '../config/firebase';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Authentication methods
  const signInWithGoogle = async () => {
    try {
      setError(null);
      const result = await signInWithPopup(auth, googleProvider);
      return result;
    } catch (error) {
      setError(error.message);
      throw error;
    }
  };

  const signInWithGitHub = async () => {
    try {
      setError(null);
      const result = await signInWithPopup(auth, githubProvider);
      return result;
    } catch (error) {
      setError(error.message);
      throw error;
    }
  };

  const signInAsGuest = async () => {
    try {
      setError(null);
      const result = await signInAnonymously(auth);
      return result;
    } catch (error) {
      setError(error.message);
      throw error;
    }
  };

  const logout = async () => {
    try {
      setError(null);
      await signOut(auth);
      // Clear local storage
      localStorage.removeItem('firebase_token');
      localStorage.removeItem('user_id');
    } catch (error) {
      setError(error.message);
      throw error;
    }
  };

  // Listen for auth state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      try {
        if (user) {
          // Get Firebase ID token
          const token = await user.getIdToken();
          
          // Store in localStorage
          localStorage.setItem('firebase_token', token);
          localStorage.setItem('user_id', user.uid);
          
          // Set user state
          setUser({
            uid: user.uid,
            email: user.email,
            displayName: user.displayName,
            photoURL: user.photoURL,
            isAnonymous: user.isAnonymous,
            providerId: user.providerData[0]?.providerId || 'anonymous',
            emailVerified: user.emailVerified,
            createdAt: user.metadata.creationTime,
            lastLoginAt: user.metadata.lastSignInTime
          });

          console.log(`User authenticated: ${user.email || 'Anonymous'}`);
        } else {
          // Clear state and storage
          setUser(null);
          localStorage.removeItem('firebase_token');
          localStorage.removeItem('user_id');
          console.log('User signed out');
        }
      } catch (error) {
        console.error('Auth state change error:', error);
        setError(error.message);
      } finally {
        setLoading(false);
      }
    });

    return unsubscribe;
  }, []);

  // Refresh token when needed
  const refreshToken = async () => {
    if (user && auth.currentUser) {
      try {
        const token = await auth.currentUser.getIdToken(true);
        localStorage.setItem('firebase_token', token);
        return token;
      } catch (error) {
        console.error('Token refresh failed:', error);
        throw error;
      }
    }
    return null;
  };

  const value = {
    user,
    loading,
    error,
    signInWithGoogle,
    signInWithGitHub,
    signInAsGuest,
    logout,
    refreshToken,
    isAuthenticated: !!user && !user.isAnonymous,
    isAnonymous: user?.isAnonymous || false
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};