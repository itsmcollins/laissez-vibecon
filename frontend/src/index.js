import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { PrivyProvider } from '@privy-io/react-auth';
import App from './App';
import './index.css';

const privyAppId = process.env.REACT_APP_PRIVY_APP_ID;

if (!privyAppId) {
  // eslint-disable-next-line no-console
  console.warn('Missing REACT_APP_PRIVY_APP_ID environment variable');
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <PrivyProvider
      appId={privyAppId}
      config={{
        loginMethods: ['google'],
        appearance: { theme: 'dark' },
        embeddedWallets: { createOnLogin: 'off' },
      }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </PrivyProvider>
  </React.StrictMode>
);