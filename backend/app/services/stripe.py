"""Stripe integration for paywall and subscriptions."""

import stripe
from fastapi import HTTPException, Request
from ..config import settings

stripe.api_key = settings.stripe_secret_key


class StripeService:
    """Handles Stripe operations."""
    
    def __init__(self):
        self.webhook_secret = settings.stripe_webhook_secret
    
    async def create_checkout_session(self, user_id: str, email: str) -> str:
        """Create a Stripe Checkout session for subscription."""
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price": "price_1Nv2jvB2pR47p4fQKqjGpW0K",  # TODO: replace with actual price ID
                    "quantity": 1,
                }],
                mode="subscription",
                customer_email=email,
                metadata={"user_id": user_id},
                success_url="http://localhost:3000/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="http://localhost:3000/cancel",
            )
            return session.url
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")
    
    async def verify_webhook_signature(self, request: Request, payload: bytes) -> stripe.Event:
        """Verify Stripe webhook signature."""
        signature = request.headers.get("stripe-signature")
        if not signature:
            raise HTTPException(status_code=400, detail="Missing stripe-signature header")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return event
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")
    
    async def handle_checkout_session_completed(self, session: stripe.checkout.Session):
        """Handle successful checkout session."""
        user_id = session.metadata.get("user_id")
        customer_email = session.customer_email
        
        # TODO: update user subscription status in database
        # For now, just log
        print(f"User {user_id} ({customer_email}) subscribed")
    
    async def handle_webhook(self, request: Request):
        """Process Stripe webhook."""
        payload = await request.body()
        event = await self.verify_webhook_signature(request, payload)
        
        # Handle event types
        if event.type == "checkout.session.completed":
            session = event.data.object
            await self.handle_checkout_session_completed(session)
            return {"status": "success"}
        
        # Return 200 for unhandled event types (acknowledge receipt)
        return {"status": "received"}