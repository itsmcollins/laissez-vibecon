import React, { useRef } from 'react';
import { X, Download } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { Button } from './ui/button';

export default function AgentBusinessCard({ isOpen, onClose, agent }) {
  const cardRef = useRef(null);

  if (!isOpen || !agent) return null;

  // Generate bot URL (placeholder)
  const botUrl = `https://t.me/${agent.name.replace(/\s+/g, '_').toLowerCase()}_bot`;
  const apiUrl = `https://api.laissez.io/agent/${agent.id || '123456'}`;

  const handleDownloadPNG = async () => {
    if (!cardRef.current) return;

    try {
      // Using html2canvas would be ideal, but for now we'll use a simple approach
      // In a real implementation, you'd want to install html2canvas
      alert('PNG download functionality - to be implemented with html2canvas library');
    } catch (error) {
      console.error('Error downloading PNG:', error);
    }
  };

  const handleDownloadHTML = () => {
    const htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${agent.name} - Laissez Agent</title>
  <style>
    body {
      font-family: system-ui, -apple-system, sans-serif;
      background: #0a0a0a;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
      padding: 20px;
    }
    .card {
      background: #0f0f0f;
      border: 1px solid #444;
      border-radius: 16px;
      padding: 48px;
      max-width: 600px;
      width: 100%;
      text-align: center;
    }
    .logo {
      font-family: Georgia, serif;
      font-size: 24px;
      color: #d1d5db;
      letter-spacing: 4px;
      margin-bottom: 32px;
    }
    h1 {
      font-size: 32px;
      font-weight: 300;
      color: #e5e7eb;
      margin-bottom: 16px;
    }
    .subtitle {
      font-size: 14px;
      color: #9ca3af;
      margin-bottom: 32px;
    }
    .qr-code {
      display: inline-block;
      padding: 16px;
      background: white;
      border-radius: 12px;
      margin-bottom: 24px;
    }
    .info {
      font-size: 12px;
      color: #6b7280;
      margin-top: 16px;
    }
    .api-url {
      font-family: monospace;
      font-size: 11px;
      color: #9ca3af;
      background: #1a1a1a;
      padding: 8px 12px;
      border-radius: 6px;
      margin-top: 16px;
      word-break: break-all;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">LAISSEZ</div>
    <h1>${agent.name}</h1>
    <div class="subtitle">AI Agent Platform</div>
    <div class="qr-code">
      <!-- QR Code SVG would go here -->
      <svg width="200" height="200" viewBox="0 0 200 200">
        <rect width="200" height="200" fill="#ffffff"/>
        <text x="100" y="100" text-anchor="middle" dominant-baseline="middle" fill="#000" font-size="12">QR Code</text>
      </svg>
    </div>
    <div class="info">Scan to start chatting</div>
    <div class="api-url">${apiUrl}</div>
  </div>
</body>
</html>
    `.trim();

    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${agent.name.replace(/\s+/g, '_')}_card.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleCopyScript = () => {
    const scriptContent = `
<!-- Laissez Agent Card Widget -->
<div id="laissez-agent-card-${agent.id || '123456'}" style="max-width: 600px; margin: 0 auto;"></div>
<script>
  (function() {
    const card = document.getElementById('laissez-agent-card-${agent.id || '123456'}');
    card.innerHTML = \`
      <div style="background: #0f0f0f; border: 1px solid #444; border-radius: 16px; padding: 48px; text-align: center; font-family: system-ui, -apple-system, sans-serif;">
        <div style="font-family: Georgia, serif; font-size: 24px; color: #d1d5db; letter-spacing: 4px; margin-bottom: 32px;">LAISSEZ</div>
        <h1 style="font-size: 32px; font-weight: 300; color: #e5e7eb; margin-bottom: 16px;">${agent.name}</h1>
        <div style="font-size: 14px; color: #9ca3af; margin-bottom: 32px;">AI Agent Platform</div>
        <div style="font-size: 12px; color: #6b7280; margin-top: 16px;">Visit our platform to interact with this agent</div>
        <div style="font-family: monospace; font-size: 11px; color: #9ca3af; background: #1a1a1a; padding: 8px 12px; border-radius: 6px; margin-top: 16px; word-break: break-all;">${apiUrl}</div>
      </div>
    \`;
  })();
</script>
    `.trim();

    navigator.clipboard.writeText(scriptContent).then(() => {
      alert('Script copied to clipboard!');
    });
  };

  return (
    <div 
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div 
        className="bg-[#0f0f0f] border border-gray-700 rounded-2xl max-w-2xl w-full relative"
        onClick={(e) => e.stopPropagation()}
        data-testid="business-card-modal"
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-200 z-10"
          data-testid="close-card-button"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Business Card */}
        <div ref={cardRef} className="p-12 text-center">
          {/* Logo */}
          <div className="text-2xl font-light text-gray-300 tracking-widest mb-8" style={{ fontFamily: 'Georgia, serif' }}>
            LAISSEZ
          </div>

          {/* Agent Name */}
          <h1 className="text-4xl font-light text-gray-200 mb-4">
            {agent.name}
          </h1>
          <p className="text-sm text-gray-500 mb-8">AI Agent Platform</p>

          {/* QR Code */}
          <div className="inline-block p-4 bg-white rounded-xl mb-6">
            <QRCodeSVG 
              value={botUrl} 
              size={200}
              level="H"
              includeMargin={false}
            />
          </div>

          {/* Info */}
          <p className="text-xs text-gray-500 mb-4">Scan to start chatting</p>
          
          {/* API URL */}
          <div className="bg-[#1a1a1a] border border-gray-800 rounded-lg p-3 mb-6">
            <p className="text-xs text-gray-400 font-mono break-all">{apiUrl}</p>
          </div>

          {/* Download Options */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button
              onClick={handleDownloadPNG}
              className="bg-transparent border border-gray-600 text-gray-300 hover:bg-gray-800 rounded-lg px-4 py-2 text-sm font-normal"
              data-testid="download-png-button"
            >
              <Download className="h-4 w-4 mr-2" />
              Download PNG
            </Button>
            <Button
              onClick={handleDownloadHTML}
              className="bg-transparent border border-gray-600 text-gray-300 hover:bg-gray-800 rounded-lg px-4 py-2 text-sm font-normal"
              data-testid="download-html-button"
            >
              <Download className="h-4 w-4 mr-2" />
              Download HTML
            </Button>
            <Button
              onClick={handleCopyScript}
              className="bg-transparent border border-gray-600 text-gray-300 hover:bg-gray-800 rounded-lg px-4 py-2 text-sm font-normal"
              data-testid="copy-script-button"
            >
              <Download className="h-4 w-4 mr-2" />
              Copy Script
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
