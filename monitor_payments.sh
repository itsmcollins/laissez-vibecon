#!/bin/bash
# Real-time payment flow monitoring script

echo "=========================================="
echo "  PAYMENT FLOW MONITOR"
echo "=========================================="
echo ""
echo "Watching backend logs for payment activity..."
echo "Press Ctrl+C to stop"
echo ""
echo "=========================================="
echo ""

# Watch backend logs and highlight payment-related lines
tail -f /var/log/supervisor/backend.out.log | grep --line-buffered -E \
  "Telegram message received|linked|balance|payment|Transaction|tx_hash|wallet|USDC|session signer|delegated" \
  --color=always
