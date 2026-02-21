"""Webhook endpoints."""

from fastapi import APIRouter, Request, HTTPException

from ..services.stripe import StripeService

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks."""
    stripe_service = StripeService()
    
    try:
        result = await stripe_service.handle_webhook(request)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")