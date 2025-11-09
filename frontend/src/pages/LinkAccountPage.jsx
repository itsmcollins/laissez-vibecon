import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { usePrivy } from '@privy-io/react-auth';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import { Toaster } from '../components/ui/sonner';

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
  const [status, setStatus] = useState('idle');
  const [loading, setLoading] = useState(false);
  const [manualCode, setManualCode] = useState('');
  const hasLinkedRef = useRef(false);

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

    if (!authenticated || hasLinkedRef.current) {
      return;
    }

    const finalizeLink = async () => {
      try {
        setLoading(true);
        setStatus('linking');
        const token = await getAccessToken();

        if (!token) {
          throw new Error('Missing Privy access token');
        }

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

        sessionStorage.removeItem(STORAGE_KEY);
        hasLinkedRef.current = true;
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

