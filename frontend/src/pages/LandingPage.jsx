import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePrivy } from '@privy-io/react-auth';
import { Button } from '../components/ui/button';

const LOGO_URL = 'https://customer-assets.emergentagent.com/job_design-refresh-81/artifacts/hbva0jbg_laissez-logo.png';

export default function LandingPage() {
  const navigate = useNavigate();
  const { authenticated, ready } = usePrivy();

  useEffect(() => {
    if (ready && authenticated) {
      navigate('/dashboard');
    }
  }, [ready, authenticated, navigate]);

  const handleSignIn = () => {
    navigate('/auth');
  };

  const handleBookDemo = () => {
    // Placeholder - do nothing for now
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-8">
      {/* Logo + Text */}
      <div className="flex flex-col items-center mb-16">
        <img 
          src={LOGO_URL} 
          alt="Laissez" 
          className="h-20 w-auto mb-4"
          data-testid="landing-logo"
        />
        <h1 className="text-4xl font-light text-gray-300 tracking-widest" style={{ fontFamily: 'Georgia, serif' }}>
          LAISSEZ
        </h1>
      </div>

      {/* Buttons */}
      <div className="flex flex-col sm:flex-row gap-4">
        <Button
          onClick={handleSignIn}
          data-testid="sign-in-button"
          className="px-12 py-6 text-base font-normal bg-transparent border-2 border-gray-500 text-gray-300 hover:bg-gray-800 rounded-full"
        >
          Sign In
        </Button>
        <Button
          onClick={handleBookDemo}
          data-testid="book-demo-button"
          className="px-12 py-6 text-base font-normal bg-transparent border-2 border-gray-500 text-gray-300 hover:bg-gray-800 rounded-full"
        >
          Book a Demo
        </Button>
      </div>
    </div>
  );
}
