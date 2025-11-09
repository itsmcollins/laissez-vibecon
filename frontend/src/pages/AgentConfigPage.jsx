import React, { useMemo, useState, useEffect } from 'react';
import { Minus, Plus, Trash2, Link as LinkIcon } from 'lucide-react';
import { usePrivy } from '@privy-io/react-auth';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Toaster } from '../components/ui/sonner';
import { toast } from 'sonner';
import '../App.css';

export default function AgentConfigPage() {
  const { getAccessToken, user, logout } = usePrivy();
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    botToken: '',
    price: 0.001,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [linkedAccounts, setLinkedAccounts] = useState([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [unlinkingId, setUnlinkingId] = useState(null);

  const displayName = useMemo(() => {
    if (!user) return null;
    if (user.email?.address) return user.email.address;
    if (user.wallet?.address) return user.wallet.address;
    return user.id;
  }, [user]);

  // Fetch linked accounts on mount
  useEffect(() => {
    fetchLinkedAccounts();
  }, []);

  const fetchLinkedAccounts = async () => {
    try {
      setLoadingAccounts(true);
      const token = await getAccessToken();
      if (!token) {
        console.error('No access token available');
        setLinkedAccounts([]);
        return;
      }

      const response = await fetch('/api/linked-accounts', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();
      if (response.ok && data.success) {
        // Ensure data.data is an array before setting
        const accounts = Array.isArray(data.data) ? data.data : [];
        setLinkedAccounts(accounts);
      } else {
        console.error('Failed to fetch linked accounts:', data);
        setLinkedAccounts([]);
      }
    } catch (error) {
      console.error('Error fetching linked accounts:', error);
      setLinkedAccounts([]);
    } finally {
      setLoadingAccounts(false);
    }
  };

  const handleUnlinkAccount = async (accountId) => {
    if (!window.confirm('Are you sure you want to unlink this account? You will need to link it again to use it.')) {
      return;
    }

    try {
      setUnlinkingId(accountId);
      const token = await getAccessToken();
      if (!token) {
        toast.error('Missing authentication token');
        return;
      }

      const response = await fetch(`/api/linked-accounts/${accountId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();
      if (response.ok && data.success) {
        toast.success('Account unlinked successfully');
        // Refresh the list
        fetchLinkedAccounts();
      } else {
        toast.error('Failed to unlink account', {
          description: data.detail || 'Please try again.',
        });
      }
    } catch (error) {
      toast.error('Network error', {
        description: 'Unable to unlink account. Please try again.',
      });
      console.error('Error unlinking account:', error);
    } finally {
      setUnlinkingId(null);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handlePriceChange = (e) => {
    const value = parseFloat(e.target.value);
    if (!Number.isNaN(value) && value >= 0.001) {
      setFormData((prev) => ({ ...prev, price: value }));
    }
  };

  const incrementPrice = () => {
    setFormData((prev) => ({
      ...prev,
      price: parseFloat((prev.price + 0.001).toFixed(3)),
    }));
  };

  const decrementPrice = () => {
    setFormData((prev) => ({
      ...prev,
      price: Math.max(0.001, parseFloat((prev.price - 0.001).toFixed(3))),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const authorizationToken = await getAccessToken();

      if (!authorizationToken) {
        toast.error('Missing Privy access token', {
          description: 'Please re-authenticate and try again.',
        });
        return;
      }

      const response = await fetch('/api/agents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authorizationToken}`,
        },
        body: JSON.stringify({
          name: formData.name,
          url: formData.url,
          bot_token: formData.botToken,
          price: formData.price,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        toast.success('Agent configuration saved successfully!', {
          description: data.webhook_info?.webhook_url
            ? 'Telegram webhook has been set up.'
            : 'Configuration saved to database.',
        });
        setFormData({
          name: '',
          url: '',
          botToken: '',
          price: 0.001,
        });
      } else {
        toast.error('Failed to save configuration', {
          description: data.detail || 'Please try again.',
        });
      }
    } catch (error) {
      toast.error('Network error', {
        description: 'Unable to connect to the server. Please try again.',
      });
      console.error('Error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-4xl font-bold text-foreground">Laissez</h1>
          {displayName && (
            <div className="text-sm text-muted-foreground text-right">
              <p>Signed in as</p>
              <p className="font-medium text-foreground">{displayName}</p>
              <Button variant="ghost" size="sm" className="mt-1 p-0" onClick={logout}>
                Sign out
              </Button>
            </div>
          )}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Agent Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name">Agent Name</Label>
                <Input
                  type="text"
                  id="name"
                  name="name"
                  data-testid="agent-name-input"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  placeholder="My Amazing Agent"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="url">Agent URL</Label>
                <Input
                  type="url"
                  id="url"
                  name="url"
                  data-testid="agent-url-input"
                  value={formData.url}
                  onChange={handleInputChange}
                  required
                  placeholder="https://your-agent-url.com"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="botToken">Telegram Bot Token</Label>
                <Input
                  type="text"
                  id="botToken"
                  name="botToken"
                  data-testid="bot-token-input"
                  value={formData.botToken}
                  onChange={handleInputChange}
                  required
                  placeholder="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="price">Price (USD)</Label>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={decrementPrice}
                    data-testid="price-decrement-button"
                    disabled={formData.price <= 0.001}
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                  <Input
                    type="number"
                    id="price"
                    name="price"
                    data-testid="price-input"
                    value={formData.price}
                    onChange={handlePriceChange}
                    step="0.001"
                    min="0.001"
                    required
                    className="text-center font-mono"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={incrementPrice}
                    data-testid="price-increment-button"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Minimum: $0.001 | Increment: $0.001
                </p>
              </div>

              <Button
                type="submit"
                data-testid="submit-button"
                disabled={isSubmitting}
                className="w-full"
                size="lg"
              >
                {isSubmitting ? 'Saving...' : 'Save Configuration'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Linked Accounts Section */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LinkIcon className="h-5 w-5" />
              Linked Accounts
            </CardTitle>
            <CardDescription>
              Manage your connected platform accounts
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingAccounts ? (
              <p className="text-sm text-muted-foreground">Loading linked accounts...</p>
            ) : linkedAccounts.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-sm text-muted-foreground mb-2">
                  No linked accounts yet
                </p>
                <p className="text-xs text-muted-foreground">
                  Link your Telegram or other platform accounts to use them with agents
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {linkedAccounts.map((account) => (
                  <div
                    key={account.id}
                    data-testid={`linked-account-${account.id}`}
                    className="flex items-center justify-between p-3 border rounded-lg bg-muted/50"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm capitalize">
                          {account.platform}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          ID: {account.platform_user_id}
                        </span>
                      </div>
                      {account.created_at && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Linked: {new Date(account.created_at).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      data-testid={`unlink-button-${account.id}`}
                      onClick={() => handleUnlinkAccount(account.id)}
                      disabled={unlinkingId === account.id}
                      className="text-destructive hover:text-destructive hover:bg-destructive/10"
                    >
                      {unlinkingId === account.id ? (
                        <span className="text-xs">Unlinking...</span>
                      ) : (
                        <>
                          <Trash2 className="h-4 w-4 mr-1" />
                          <span className="text-xs">Unlink</span>
                        </>
                      )}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      <Toaster />
    </div>
  );
}


