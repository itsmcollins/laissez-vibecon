import React, { useState } from 'react';
import { DollarSign, Wallet, Plus, ExternalLink, LogOut } from 'lucide-react';
import { Button } from '../components/ui/button';
import AddAgentModal from '../components/AddAgentModal';
import AgentBusinessCard from '../components/AgentBusinessCard';

const LOGO_URL = 'https://customer-assets.emergentagent.com/job_design-refresh-81/artifacts/hbva0jbg_laissez-logo.png';
const PLACEHOLDER_AVATAR = 'https://api.dicebear.com/7.x/avataaars/svg?seed=laissez';

// Dummy transaction data for User view
const USER_TRANSACTIONS = [
  { id: 1, agent: 'Assistant Bot', bot: 'GPT-4o', query: 'How to deploy on AWS?', cost: 0.023, time: '2 mins ago' },
  { id: 2, agent: 'Code Helper', bot: 'Claude 3', query: 'Debug my React component', cost: 0.015, time: '15 mins ago' },
  { id: 3, agent: 'Research Agent', bot: 'GPT-4o', query: 'Latest AI trends 2024', cost: 0.031, time: '1 hour ago' },
  { id: 4, agent: 'Data Analyst', bot: 'Claude 3', query: 'Analyze sales data', cost: 0.042, time: '2 hours ago' },
  { id: 5, agent: 'Content Writer', bot: 'GPT-4o', query: 'Write blog post outline', cost: 0.018, time: '3 hours ago' },
];

// Dummy transaction data for Developer view
const DEV_TRANSACTIONS = [
  { id: 1, agent: 'Assistant Bot', query: 'Technical support query', earned: 0.023, time: '2 mins ago' },
  { id: 2, agent: 'Code Helper', query: 'Code review request', earned: 0.015, time: '15 mins ago' },
  { id: 3, agent: 'Research Agent', query: 'Market analysis', earned: 0.031, time: '1 hour ago' },
  { id: 4, agent: 'Data Analyst', query: 'SQL optimization', earned: 0.042, time: '2 hours ago' },
  { id: 5, agent: 'Content Writer', query: 'Content generation', earned: 0.018, time: '3 hours ago' },
];

// Dummy agent stats data
const AGENT_STATS = [
  { id: 1, agent: 'Assistant Bot', queries: 247, users: 45, earned: 12.34 },
  { id: 2, agent: 'Code Helper', queries: 189, users: 32, earned: 9.87 },
  { id: 3, agent: 'Research Agent', queries: 156, users: 28, earned: 8.21 },
  { id: 4, agent: 'Data Analyst', queries: 134, users: 19, earned: 7.45 },
  { id: 5, agent: 'Content Writer', queries: 98, users: 15, earned: 5.12 },
];

export default function DashboardPreview() {
  const [viewMode, setViewMode] = useState('user'); // 'user' or 'developer'
  const [devTab, setDevTab] = useState('agents'); // 'agents' or 'transactions'
  const [isAddAgentModalOpen, setIsAddAgentModalOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [isBusinessCardOpen, setIsBusinessCardOpen] = useState(false);

  const totalSpent = USER_TRANSACTIONS.reduce((sum, tx) => sum + tx.cost, 0).toFixed(3);
  const totalEarned = DEV_TRANSACTIONS.reduce((sum, tx) => sum + tx.earned, 0).toFixed(3);

  const handleAgentClick = (agentName) => {
    setSelectedAgent({ name: agentName, id: agentName.replace(/\s+/g, '_').toLowerCase() });
    setIsBusinessCardOpen(true);
  };

  const handleSignOut = () => {
    alert('Sign out functionality - will be connected to Privy logout');
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-gray-300 p-8" style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-12 max-w-7xl mx-auto">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <img 
            src={LOGO_URL} 
            alt="Laissez" 
            className="h-10 w-auto"
            data-testid="dashboard-logo"
          />
          <span className="text-xl font-light tracking-wider" style={{ fontFamily: 'Georgia, serif' }}>LAISSEZ</span>
        </div>

        {/* Profile & Sign Out */}
        <div className="flex items-center gap-4">
          <img 
            src={PLACEHOLDER_AVATAR} 
            alt="Profile" 
            className="h-10 w-10 rounded-full border border-gray-600"
            data-testid="profile-avatar"
          />
          <Button
            onClick={handleSignOut}
            variant="ghost"
            className="text-gray-400 hover:text-gray-200 text-sm font-normal"
            data-testid="signout-button"
          >
            <LogOut className="h-4 w-4 mr-2" />
            Sign Out
          </Button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto">
        {/* View Toggle */}
        <div className="flex items-center gap-4 mb-10">
          <div className="flex items-center border border-gray-700 rounded-full p-1 bg-[#0f0f0f]">
            <button
              onClick={() => setViewMode('user')}
              data-testid="user-view-toggle"
              className={`px-8 py-2 rounded-full transition-all text-sm font-normal ${
                viewMode === 'user' 
                  ? 'bg-gray-700 text-gray-200' 
                  : 'bg-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              User
            </button>
            <button
              onClick={() => setViewMode('developer')}
              data-testid="developer-view-toggle"
              className={`px-8 py-2 rounded-full transition-all text-sm font-normal ${
                viewMode === 'developer' 
                  ? 'bg-gray-700 text-gray-200' 
                  : 'bg-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              Dev
            </button>
          </div>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
          {/* Welcome Card */}
          <div 
            className="border border-gray-700 rounded-lg p-6 bg-[#0f0f0f]"
            data-testid="welcome-card"
          >
            <h2 className="text-lg font-normal mb-3 text-gray-300 tracking-wide">WELCOME</h2>
            <p className="text-gray-500 text-xs mb-1">Signed in with</p>
            <p className="text-gray-300 text-sm font-light">user@example.com</p>
          </div>

          {/* Spend/Earn Card */}
          <div 
            className="border border-gray-700 rounded-lg p-6 bg-[#0f0f0f]"
            data-testid={viewMode === 'user' ? 'spend-card' : 'earn-card'}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-gray-500" />
                <h2 className="text-lg font-normal text-gray-300 tracking-wide">
                  {viewMode === 'user' ? 'SPEND' : 'EARN'}
                </h2>
              </div>
              {viewMode === 'developer' && (
                <Button
                  onClick={() => setIsAddAgentModalOpen(true)}
                  className="bg-transparent border border-gray-600 text-gray-300 hover:bg-gray-800 rounded-full px-3 py-1 text-xs font-normal"
                  data-testid="add-agent-button"
                >
                  <Plus className="h-3 w-3 mr-1" />
                  Add Agent
                </Button>
              )}
            </div>
            <p className="text-gray-500 text-xs mb-2">(last month)</p>
            <p className="text-2xl font-light text-gray-200">
              ${viewMode === 'user' ? totalSpent : totalEarned}
            </p>
          </div>

          {/* Wallet Card */}
          <div 
            className="border border-gray-700 rounded-lg p-6 bg-[#0f0f0f]"
            data-testid="wallet-card"
          >
            <div className="flex items-center gap-2 mb-3">
              <Wallet className="h-4 w-4 text-gray-500" />
              <h2 className="text-lg font-normal text-gray-300 tracking-wide">WALLET BALANCE</h2>
            </div>
            <p className="text-2xl font-light text-gray-200 mb-4">$25.00</p>
            <Button 
              size="sm" 
              className="bg-transparent border border-gray-600 text-gray-300 hover:bg-gray-800 rounded-full px-4 py-2 text-sm font-normal"
              data-testid="add-funds-button"
            >
              <Plus className="h-3 w-3 mr-1" />
              Add Funds
            </Button>
          </div>
        </div>

        {/* Tabs for Developer View */}
        {viewMode === 'developer' && (
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setDevTab('agents')}
              data-testid="agents-tab"
              className={`px-6 py-2 rounded-lg transition-all text-sm font-normal border ${
                devTab === 'agents'
                  ? 'bg-gray-700 border-gray-600 text-gray-200'
                  : 'bg-transparent border-gray-700 text-gray-500 hover:text-gray-300 hover:border-gray-600'
              }`}
            >
              Agents
            </button>
            <button
              onClick={() => setDevTab('transactions')}
              data-testid="transactions-tab"
              className={`px-6 py-2 rounded-lg transition-all text-sm font-normal border ${
                devTab === 'transactions'
                  ? 'bg-gray-700 border-gray-600 text-gray-200'
                  : 'bg-transparent border-gray-700 text-gray-500 hover:text-gray-300 hover:border-gray-600'
              }`}
            >
              Transactions
            </button>
          </div>
        )}

        {/* Transactions Section */}
        <div className="border border-gray-700 rounded-lg bg-[#0f0f0f] overflow-hidden">
          {/* Table Content */}
          <div className="overflow-x-auto">
            {viewMode === 'user' ? (
              // User View - Transactions Table
              <table className="w-full" data-testid="user-transactions-table">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Agent</th>
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Bot</th>
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Query</th>
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Cost</th>
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {USER_TRANSACTIONS.map((tx) => (
                    <tr key={tx.id} className="border-b border-gray-800 hover:bg-[#151515] transition-colors">
                      <td className="p-4 text-sm text-gray-300">{tx.agent}</td>
                      <td className="p-4 text-sm text-gray-300">{tx.bot}</td>
                      <td className="p-4 text-sm text-gray-500">{tx.query}</td>
                      <td className="p-4 text-sm text-gray-300">${tx.cost.toFixed(3)}</td>
                      <td className="p-4 text-sm text-gray-500">{tx.time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : devTab === 'agents' ? (
              // Developer View - Agents Table
              <table className="w-full" data-testid="agents-stats-table">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Agent</th>
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Queries (count)</th>
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Users (count)</th>
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Earned</th>
                  </tr>
                </thead>
                <tbody>
                  {AGENT_STATS.map((agent) => (
                    <tr key={agent.id} className="border-b border-gray-800 hover:bg-[#151515] transition-colors">
                      <td className="p-4 text-sm text-gray-300">
                        <div className="flex items-center gap-2">
                          <span>{agent.agent}</span>
                          <button
                            onClick={() => handleAgentClick(agent.agent)}
                            className="text-gray-500 hover:text-gray-300 transition-colors"
                            data-testid={`agent-card-icon-${agent.id}`}
                            title="View business card"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                      <td className="p-4 text-sm text-gray-300">{agent.queries}</td>
                      <td className="p-4 text-sm text-gray-300">{agent.users}</td>
                      <td className="p-4 text-sm text-gray-300">${agent.earned.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              // Developer View - Transactions Table
              <table className="w-full" data-testid="dev-transactions-table">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Agent</th>
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Query</th>
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Earned</th>
                    <th className="text-left p-4 font-normal text-sm text-gray-400 tracking-wide">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {DEV_TRANSACTIONS.map((tx) => (
                    <tr key={tx.id} className="border-b border-gray-800 hover:bg-[#151515] transition-colors">
                      <td className="p-4 text-sm text-gray-300">{tx.agent}</td>
                      <td className="p-4 text-sm text-gray-500">{tx.query}</td>
                      <td className="p-4 text-sm text-gray-300">${tx.earned.toFixed(3)}</td>
                      <td className="p-4 text-sm text-gray-500">{tx.time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Modals */}
      <AddAgentModal 
        isOpen={isAddAgentModalOpen} 
        onClose={() => setIsAddAgentModalOpen(false)} 
      />
      <AgentBusinessCard
        isOpen={isBusinessCardOpen}
        onClose={() => setIsBusinessCardOpen(false)}
        agent={selectedAgent}
      />
    </div>
  );
}
