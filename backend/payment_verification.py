"""
Payment verification module using x402 protocol with Privy server-side payments.

This module provides proper x402 payment verification while maintaining
Privy's server-side payment flow (no client-side payments required).

Inspired by Laissez middleware pattern with facilitator verification.
"""

import base64
import json
import logging
from typing import Optional, Dict, Any, cast
from fastapi import Request
from x402.facilitator import FacilitatorClient, FacilitatorConfig
from x402.common import process_price_to_atomic_amount, find_matching_payment_requirements
from x402.types import (
    PaymentPayload,
    PaymentRequirements,
    x402PaymentRequiredResponse,
    SupportedNetworks,
)

logger = logging.getLogger(__name__)

# x402 Configuration
X402_FACILITATOR_URL = "https://x402.org/facilitator"
X402_NETWORK = "base-sepolia"
X402_VERSION = 1

# Initialize facilitator client
_facilitator_client: Optional[FacilitatorClient] = None


def get_facilitator_client() -> FacilitatorClient:
    """Get or create the facilitator client singleton."""
    global _facilitator_client
    if _facilitator_client is None:
        _facilitator_client = FacilitatorClient(
            config=FacilitatorConfig(url=X402_FACILITATOR_URL)
        )
    return _facilitator_client


def create_payment_requirements(
    price_usd: float,
    creator_wallet: str,
    resource_url: str,
    bot_token: str,
    network: str = X402_NETWORK,
) -> PaymentRequirements:
    """
    Create x402 payment requirements for an agent.
    
    Args:
        price_usd: Price in USD (e.g., 0.001)
        creator_wallet: Wallet address to receive payment
        resource_url: URL of the resource being accessed
        bot_token: Bot token for description
        network: Network to use (default: base-sepolia)
    
    Returns:
        PaymentRequirements object
    """
    # Convert price to atomic units using x402 helper
    price_str = str(price_usd)
    max_amount, asset_address, eip712_domain = process_price_to_atomic_amount(
        price_str, network
    )
    
    return PaymentRequirements(
        scheme="exact",
        network=cast(SupportedNetworks, network),
        asset=asset_address,
        max_amount_required=max_amount,
        resource=resource_url,
        description=f"Payment required to message this agent (${price_usd})",
        mime_type="application/json",
        pay_to=creator_wallet,
        max_timeout_seconds=60,
        extra=eip712_domain,
    )


def create_402_response(
    payment_requirements: PaymentRequirements,
) -> Dict[str, Any]:
    """
    Create a 402 Payment Required response.
    
    Args:
        payment_requirements: Payment requirements for the request
    
    Returns:
        Dict with status_code and body for 402 response
    """
    response_data = x402PaymentRequiredResponse(
        x402_version=X402_VERSION,
        accepts=[payment_requirements],
        error="Payment required",
    )
    
    return {
        "status_code": 402,
        "body": response_data.model_dump(by_alias=True),
    }


def decode_payment_header(payment_header: str) -> Optional[PaymentPayload]:
    """
    Decode and validate X-PAYMENT header.
    
    Args:
        payment_header: Base64-encoded payment payload
    
    Returns:
        PaymentPayload object or None if invalid
    """
    try:
        # Decode base64
        payment_json = base64.b64decode(payment_header)
        payment_dict = json.loads(payment_json)
        
        # Parse into PaymentPayload
        payment = PaymentPayload(**payment_dict)
        return payment
    
    except Exception as e:
        logger.warning(f"Failed to decode payment header: {e}")
        return None


async def verify_payment(
    payment: PaymentPayload,
    requirements: PaymentRequirements,
) -> tuple[bool, Optional[str]]:
    """
    Verify payment with x402 facilitator.
    
    Args:
        payment: Payment payload from X-PAYMENT header
        requirements: Payment requirements to verify against
    
    Returns:
        Tuple of (is_valid, error_reason)
    """
    try:
        facilitator = get_facilitator_client()
        
        # Verify with facilitator
        verify_response = await facilitator.verify(payment, requirements)
        
        if verify_response.is_valid:
            logger.info(
                f"✅ Payment verified: {payment.authorization.payer} → "
                f"{requirements.pay_to} ({requirements.max_amount_required} units)"
            )
            return True, None
        else:
            logger.warning(
                f"❌ Payment verification failed: {verify_response.invalid_reason}"
            )
            return False, verify_response.invalid_reason
    
    except Exception as e:
        logger.error(f"❌ Payment verification exception: {e}")
        return False, f"Verification error: {str(e)}"


async def check_and_verify_payment(
    request: Request,
    price_usd: float,
    creator_wallet: str,
    bot_token: str,
) -> Optional[Dict[str, Any]]:
    """
    Check if payment is required and verify if provided.
    
    This is the main function used by the webhook endpoint.
    
    Args:
        request: FastAPI request object
        price_usd: Price required in USD
        creator_wallet: Wallet address to receive payment
        bot_token: Bot token for logging
    
    Returns:
        None if payment is valid, or dict with 402 response if payment required/invalid
    """
    # Build resource URL
    resource_url = str(request.url.path)
    
    # Create payment requirements
    requirements = create_payment_requirements(
        price_usd=price_usd,
        creator_wallet=creator_wallet,
        resource_url=resource_url,
        bot_token=bot_token,
    )
    
    # Check for X-PAYMENT header
    payment_header = request.headers.get("X-PAYMENT") or request.headers.get("x-payment")
    
    if not payment_header:
        # No payment provided - return 402
        logger.info(f"💳 Payment required: ${price_usd} to {creator_wallet[:10]}...")
        return create_402_response(requirements)
    
    # Decode payment
    payment = decode_payment_header(payment_header)
    if not payment:
        logger.warning("❌ Invalid payment header format")
        return {
            "status_code": 400,
            "body": {"error": "Invalid X-PAYMENT header format"},
        }
    
    # Verify payment matches requirements
    matching_requirements = find_matching_payment_requirements(
        payment_requirements=[requirements],
        payment=payment,
    )
    
    if not matching_requirements:
        logger.warning("❌ Payment does not match requirements")
        return {
            "status_code": 402,
            "body": {
                "error": "Payment does not match requirements",
                "required": requirements.model_dump(by_alias=True),
            },
        }
    
    # Verify with facilitator
    is_valid, error_reason = await verify_payment(payment, matching_requirements)
    
    if not is_valid:
        logger.warning(f"❌ Payment verification failed: {error_reason}")
        return {
            "status_code": 402,
            "body": {
                "error": f"Payment verification failed: {error_reason}",
                "required": requirements.model_dump(by_alias=True),
            },
        }
    
    # Payment is valid!
    logger.info(f"✅ Payment verified successfully for bot {bot_token[:20]}...")
    return None


async def settle_payment(
    payment: PaymentPayload,
    requirements: PaymentRequirements,
    max_retries: int = 3,
) -> tuple[bool, Optional[str]]:
    """
    Settle payment with x402 facilitator.
    
    This should be called after successfully processing the request.
    
    Args:
        payment: Payment payload
        requirements: Payment requirements
        max_retries: Maximum number of settlement retry attempts
    
    Returns:
        Tuple of (success, error_reason)
    """
    facilitator = get_facilitator_client()
    
    for attempt in range(max_retries):
        try:
            settle_response = await facilitator.settle(payment, requirements)
            
            if settle_response.success:
                logger.info(f"✅ Payment settled successfully")
                return True, None
            else:
                error_reason = settle_response.error_reason
                if attempt < max_retries - 1:
                    logger.warning(
                        f"⚠️ Settlement attempt {attempt + 1} failed: {error_reason}"
                    )
                else:
                    logger.error(f"❌ Payment settlement failed: {error_reason}")
                    return False, error_reason
        
        except Exception as e:
            error_reason = f"Settlement exception: {str(e)}"
            if attempt < max_retries - 1:
                logger.warning(f"⚠️ Settlement attempt {attempt + 1} exception: {e}")
            else:
                logger.error(f"❌ Payment settlement exception: {e}")
                return False, error_reason
    
    return False, "Settlement failed after all retries"
