// Firebase configuration for React app
import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, GithubAuthProvider } from 'firebase/auth';

// Your Firebase config from Firebase console
const firebaseConfig = {
  apiKey: "AIzaSyAXsg5zIYSs3-AwFGhrz1XkPeqRLgyjhQc",
  authDomain: "scholar-quest-b1f4d.firebaseapp.com",
  projectId: "scholar-quest-b1f4d",
  storageBucket: "scholar-quest-b1f4d.firebasestorage.app",
  messagingSenderId: "609511869465",
  appId: "1:609511869465:web:bddf3f1e11230c91f3ee88",
  measurementId: "G-BJ1PP4E7CG"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Auth
export const auth = getAuth(app);

// Initialize Auth Providers
export const googleProvider = new GoogleAuthProvider();
export const githubProvider = new GithubAuthProvider();

// Optional: Configure providers
googleProvider.setCustomParameters({
  prompt: 'select_account'
});

githubProvider.setCustomParameters({
  prompt: 'select_account'
});

export default app;