#!/bin/bash
# Helper script to watch payment-related logs in real-time

echo "=========================================="
echo "  Watching Payment Flow Logs"
echo "=========================================="
echo ""
echo "This will show:"
echo "  - Telegram webhooks"
echo "  - Payment function calls"
echo "  - Transaction results"
echo "  - Errors and warnings"
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "=========================================="
echo ""

# Follow backend logs and filter for payment-related lines
tail -f /var/log/supervisor/backend.*.log 2>/dev/null | grep --line-buffered -E "(TELEGRAM WEBHOOK|PAYMENT FUNCTION|Transaction|💸|💳|💵|💰|❌|✅|⚠️|🔍|📋|Telegram user|wallet|balance|Privy|delegated)"
