import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePrivy } from '@privy-io/react-auth';
import { Button } from '../components/ui/button';

const LOGO_URL = 'https://customer-assets.emergentagent.com/job_design-refresh-81/artifacts/hbva0jbg_laissez-logo.png';

export default function AuthPage() {
  const navigate = useNavigate();
  const { login, authenticated, ready } = usePrivy();

  useEffect(() => {
    if (ready && authenticated) {
      navigate('/dashboard');
    }
  }, [ready, authenticated, navigate]);

  const handleSignIn = async () => {
    try {
      await login({ loginMethods: ['google'] });
    } catch (error) {
      console.error('Login error:', error);
    }
  };

  const handleBack = () => {
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-8">
      {/* Logo */}
      <div className="flex flex-col items-center mb-12">
        <img 
          src={LOGO_URL} 
          alt="Laissez" 
          className="h-16 w-auto mb-4"
          data-testid="auth-logo"
        />
        <h1 className="text-3xl font-light text-gray-300 tracking-widest mb-8" style={{ fontFamily: 'Georgia, serif' }}>
          LAISSEZ
        </h1>
      </div>

      {/* Auth Card */}
      <div className="w-full max-w-md border border-gray-700 rounded-lg p-8 bg-[#0f0f0f]">
        <h2 className="text-xl font-light text-gray-300 mb-2 text-center">Sign in to continue</h2>
        <p className="text-sm text-gray-500 mb-8 text-center">
          Please authenticate with Google to access the Laissez platform.
        </p>
        
        <Button
          onClick={handleSignIn}
          data-testid="google-signin-button"
          className="w-full py-6 text-base font-normal bg-transparent border border-gray-600 text-gray-300 hover:bg-gray-800 rounded-lg mb-4"
        >
          Continue with Google
        </Button>
        
        <Button
          onClick={handleBack}
          variant="ghost"
          className="w-full text-sm text-gray-500 hover:text-gray-300"
        >
          ← Back to home
        </Button>
      </div>
    </div>
  );
}
