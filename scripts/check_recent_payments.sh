#!/bin/bash
# Helper script to check recent payment attempts from logs

echo "=========================================="
echo "  Recent Payment Attempts"
echo "=========================================="
echo ""

# Get the last 500 lines and show payment-related activity
echo "Last Payment Function Calls:"
echo "----------------------------"
tail -n 500 /var/log/supervisor/backend.*.log 2>/dev/null | grep -A 30 "PAYMENT FUNCTION START" | tail -50

echo ""
echo "=========================================="
echo ""
echo "Recent Transaction Results:"
echo "----------------------------"
tail -n 500 /var/log/supervisor/backend.*.log 2>/dev/null | grep -E "(TRANSACTION SENT SUCCESSFULLY|TRANSACTION FAILED|Payment failed)" | tail -10

echo ""
echo "=========================================="
echo ""
echo "Recent Wallet Issues:"
echo "----------------------------"
tail -n 500 /var/log/supervisor/backend.*.log 2>/dev/null | grep -E "(delegated|No delegated wallet|NOT delegated)" | tail -10

echo ""
echo "=========================================="
echo ""
echo "To see live logs, run:"
echo "  /app/scripts/watch_payment_logs.sh"
echo ""
