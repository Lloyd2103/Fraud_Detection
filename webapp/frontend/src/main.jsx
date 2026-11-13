import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { AuthProvider } from './store/AuthContext';
import { AlertsWsProvider } from './store/AlertsWsContext';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <AlertsWsProvider>
        <App />
      </AlertsWsProvider>
    </AuthProvider>
  </React.StrictMode>
);
