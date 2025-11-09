import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { usePrivy, useSessionSigners, useWallets } from '@privy-io/react-auth';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import { Toaster } from '../components/ui/sonner';
import { Buffer } from 'buffer';

// Polyfill Buffer for browser environment
window.Buffer = Buffer;

const KEY_QUORUM_ID = process.env.REACT_APP_LAISSEZ_KEY_QUORUM_ID || 'wsu5txzij9hcntkyf9rfw5zh';

const STORAGE_KEY = 'laissez_link_code';

const statusCopy = {
  idle: 'Ready to link your account.',
  loggingIn: 'Redirecting to Google...',
  linking: 'Completing link...',
  success: 'All set! Your account has been linked.',
  missingCode:
    'No pending link code was found. Please start the linking flow from the originating platform.',
  error: 'We could not complete the link. Please try again.',
};

export default function LinkAccountPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { login, ready, authenticated, getAccessToken, user } = usePrivy();
  const { addSessionSigners } = useSessionSigners();
  const { wallets } = useWallets();
  const [status, setStatus] = useState('idle');
  const [loading, setLoading] = useState(false);
  const [manualCode, setManualCode] = useState('');
  const linkingInProgressRef = useRef(false);
  const completedCodeRef = useRef(null);

  const queryCode = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get('code') ?? '';
  }, [location.search]);

  useEffect(() => {
    if (queryCode) {
      sessionStorage.setItem(STORAGE_KEY, queryCode);
      setManualCode('');
    }
  }, [queryCode]);

  const code = useMemo(() => {
    if (queryCode) return queryCode;
    if (manualCode) return manualCode;
    return sessionStorage.getItem(STORAGE_KEY) ?? '';
  }, [queryCode, manualCode]);

  useEffect(() => {
    if (!ready) {
      return;
    }

    if (!code) {
      setStatus('missingCode');
      return;
    }

    if (!authenticated) {
      return;
    }

    if (completedCodeRef.current === code) {
      console.log('Link flow already completed for this code; skipping duplicate invocation.');
      return;
    }

    if (linkingInProgressRef.current) {
      console.log('Linking already in progress; ignoring duplicate invocation.');
      return;
    }

    const finalizeLink = async () => {
      try {
        linkingInProgressRef.current = true;
        setLoading(true);
        setStatus('linking');
        const token = await getAccessToken();

        if (!token) {
          throw new Error('Missing Privy access token');
        }

        // Add session signers FIRST, before calling backend
        // This prevents race condition where background task runs before signers are added
        console.log('=== SESSION SIGNER SETUP START ===');
        console.log('KEY_QUORUM_ID:', KEY_QUORUM_ID);
        console.log('User object:', user);
        console.log('User linked accounts:', user?.linkedAccounts);
        
        // Get wallet from user.linkedAccounts
        const walletAccount = user?.linkedAccounts?.find(
          account => account.type === 'wallet' && account.chainType === 'ethereum'
        );
        
        console.log('Found wallet account:', walletAccount);
        
        if (walletAccount && walletAccount.address) {
          // CHECK if wallet is already delegated before attempting to add signers
          if (walletAccount.delegated === true) {
            console.log('✅ Wallet already has session signers (delegated: true), skipping addSessionSigners');
            console.log('Wallet address:', walletAccount.address);
            toast.success('Wallet already configured for payments');
          } else {
            // Wallet NOT delegated - add session signers
            try {
              console.log(`⏳ Adding session signer to wallet: ${walletAccount.address}`);
              console.log('Wallet delegated status:', walletAccount.delegated);
              console.log('Calling addSessionSigners with:', {
                address: walletAccount.address,
                signers: [{
                  signerId: KEY_QUORUM_ID,
                  policyIds: []
                }]
              });
              
              const result = await addSessionSigners({
                address: walletAccount.address,
                signers: [
                  {
                    signerId: KEY_QUORUM_ID,
                    policyIds: [] // No policies - unrestricted access for payments
                  }
                ]
              });
              
              console.log('✅ Session signers added successfully!');
              console.log('addSessionSigners result:', result);
              toast.success('Wallet configured for payments');
            } catch (signerError) {
              console.error('❌ Failed to add session signers:', signerError);
              console.error('Error details:', {
                name: signerError?.name,
                message: signerError?.message,
                stack: signerError?.stack
              });
              
              // Check if it's a duplicate signer error (shouldn't happen now but keep as safety)
              if (signerError.message && signerError.message.includes('Duplicate signer')) {
                console.log('ℹ️  Session signers already added (duplicate error - this should not happen with our check)');
                toast.success('Wallet already configured for payments');
              } else {
                // Real error - show to user
                toast.error('Wallet delegation failed: ' + signerError.message);
              }
            }
          }
        } else {
          console.warn('⚠️ No wallet found in user.linkedAccounts');
          console.warn('User has', user?.linkedAccounts?.length || 0, 'linked accounts');
          toast.warning('No wallet found. Please create a wallet first.');
        }
        
        console.log('=== SESSION SIGNER SETUP END ===');

        // NOW call the backend after session signers are added
        console.log('📡 Calling backend to complete account link...');
        const response = await fetch('/api/link/complete', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ code }),
        });

        const payload = await response.json();

        if (!response.ok) {
          throw new Error(payload.detail || 'Failed to complete account link');
        }

        console.log('✅ Backend link complete successful');

        completedCodeRef.current = code;
        sessionStorage.removeItem(STORAGE_KEY);
        setStatus('success');

        toast.success('Account linked');

        setTimeout(() => {
          navigate('/', { replace: true });
        }, 2500);
      } catch (error) {
        console.error(error);
        toast.error('Unable to complete link', {
          description: error.message,
        });
        setStatus('error');
      } finally {
        linkingInProgressRef.current = false;
        setLoading(false);
      }
    };

    finalizeLink();
  }, [ready, authenticated, code, getAccessToken, navigate]);

  const handleLogin = () => {
    setStatus('loggingIn');
    login({ loginMethods: ['google'] }).catch((error) => {
      console.error(error);
      toast.error('Login failed', {
        description: error.message,
      });
      setStatus('error');
    });
  };

  useEffect(() => {
    if (ready && !code) {
      setStatus('missingCode');
    }
  }, [ready, code]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Link Your Account</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-sm text-muted-foreground">{statusCopy[status]}</p>

          {!queryCode && (
            <div className="space-y-2">
              <Label htmlFor="manual-code">Have a link code?</Label>
              <Input
                id="manual-code"
                placeholder="Paste your link code"
                value={manualCode}
                onChange={(event) => setManualCode(event.target.value.trim())}
              />
            </div>
          )}

          {!ready && <p className="text-sm text-muted-foreground">Initializing authentication...</p>}

          {ready && !authenticated && (
            <Button type="button" className="w-full" onClick={handleLogin} disabled={loading}>
              Continue with Google
            </Button>
          )}

          {ready && authenticated && (
            <div className="space-y-4">
              {user && (
                <div className="rounded-md bg-muted p-3 text-sm">
                  <p className="font-medium text-foreground">Signed in as</p>
                  <p>{user.email?.address ?? user.id}</p>
                </div>
              )}

              {loading && (
                <p className="text-sm text-muted-foreground">
                  Please wait while we finish linking your account…
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
      <Toaster position="top-center" />
    </div>
  );
}
