"""Billing & Subscription API routes — Phase 12.

Endpoints:
- GET  /billing/plans               — Get available pricing plans
- POST /billing/checkout             — Create Stripe checkout session
- POST /billing/portal               — Create Stripe customer portal link
- GET  /billing/subscription         — Get current subscription
- POST /billing/subscription/cancel  — Cancel subscription
- POST /billing/subscription/resume  — Resume canceled subscription
- GET  /billing/invoices             — List invoices
- GET  /billing/upcoming-invoice     — Preview next invoice
- POST /billing/webhooks/stripe      — Stripe webhook handler
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.database import User, PlanTier
from app.models.billing import (
    Subscription, Invoice, SubscriptionStatus, BillingCycle, PRICING,
)
from app.api.auth_middleware import get_current_active_user
from app.services.billing_service import (
    get_billing_service,
    get_audit_logger,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing & Monetization (Phase 12)"])


# =============================================================================
# Request / Response Models
# =============================================================================

class CheckoutRequest(BaseModel):
    plan: str = Field(description="Plan: pro, team, enterprise")
    billing_cycle: str = Field(default="monthly", description="monthly or yearly")
    trial_days: Optional[int] = Field(default=None, description="Trial period in days")

class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str

class SubscriptionResponse(BaseModel):
    id: str
    plan: str
    billing_cycle: str
    status: str
    amount_cents: int
    currency: str
    current_period_end: Optional[str]
    cancel_at: Optional[str]
    trial_ends_at: Optional[str]

class InvoiceResponse(BaseModel):
    id: str
    status: str
    total_cents: int
    currency: str
    invoice_pdf: Optional[str]
    created_at: str

class PlanResponse(BaseModel):
    plans: dict


# =============================================================================
# Plans
# =============================================================================

@router.get("/plans", response_model=PlanResponse)
async def get_plans():
    """Get all available pricing plans."""
    plans = {}
    for plan_key, plan_data in PRICING.items():
        plans[plan_key] = {
            "name": plan_data["name"],
            "monthly_price": plan_data["monthly_cents"] / 100,
            "yearly_price": plan_data["yearly_cents"] / 100,
            "yearly_monthly_price": round(plan_data["yearly_cents"] / 1200, 2),
            "yearly_savings_pct": (
                round((1 - plan_data["yearly_cents"] / (plan_data["monthly_cents"] * 12)) * 100)
                if plan_data["monthly_cents"] > 0 else 0
            ),
            "currency": "usd",
        }
    return PlanResponse(plans=plans)


# =============================================================================
# Checkout
# =============================================================================

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout session for plan purchase."""
    billing = get_billing_service()

    if not billing.is_available:
        raise HTTPException(503, "Billing service not configured. Set STRIPE_SECRET_KEY.")

    # Validate plan
    plan_data = PRICING.get(request.plan)
    if not plan_data:
        raise HTTPException(400, f"Invalid plan: {request.plan}. Available: {list(PRICING.keys())}")

    if request.plan == "free":
        raise HTTPException(400, "No checkout needed for free plan")

    # Get price ID
    price_id = plan_data.get(
        f"stripe_price_{request.billing_cycle}",
        plan_data.get("stripe_price_monthly"),
    )
    if not price_id:
        raise HTTPException(400, "Price not configured for this plan/cycle")

    # Ensure Stripe customer exists
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id).order_by(Subscription.created_at.desc())
    )
    existing = result.scalar_one_or_none()
    
    customer_id = existing.stripe_customer_id if existing else None
    if not customer_id:
        customer_id = billing.create_customer(
            email=user.email,
            name=user.display_name,
            user_id=user.id,
        )
        if not customer_id:
            raise HTTPException(500, "Failed to create billing customer")

    # Create checkout session
    session = billing.create_checkout_session(
        customer_id=customer_id,
        price_id=price_id,
        user_id=user.id,
        trial_days=request.trial_days,
    )

    if not session:
        raise HTTPException(500, "Failed to create checkout session")

    # Log
    audit = get_audit_logger()
    await audit.log(
        action="plan_upgrade",
        user_id=user.id,
        resource_type="subscription",
        description=f"Checkout initiated for {request.plan} ({request.billing_cycle})",
        db_session=db,
    )

    return CheckoutResponse(
        checkout_url=session["url"],
        session_id=session["session_id"],
    )


# =============================================================================
# Portal
# =============================================================================

@router.post("/portal")
async def create_portal(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Customer Portal session for managing billing."""
    billing = get_billing_service()
    if not billing.is_available:
        raise HTTPException(503, "Billing service not configured")

    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.stripe_customer_id.isnot(None),
        )
    )
    sub = result.scalar_one_or_none()

    if not sub or not sub.stripe_customer_id:
        raise HTTPException(404, "No billing account found. Subscribe to a plan first.")

    portal_url = billing.create_portal_session(sub.stripe_customer_id)
    if not portal_url:
        raise HTTPException(500, "Failed to create portal session")

    return {"url": portal_url}


# =============================================================================
# Subscription Management
# =============================================================================

@router.get("/subscription", response_model=Optional[SubscriptionResponse])
async def get_subscription(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's active subscription."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status.in_([
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING,
                SubscriptionStatus.PAST_DUE,
            ]),
        ).order_by(Subscription.created_at.desc())
    )
    sub = result.scalar_one_or_none()

    if not sub:
        return SubscriptionResponse(
            id="", plan="free", billing_cycle="monthly",
            status="active", amount_cents=0, currency="usd",
            current_period_end=None, cancel_at=None, trial_ends_at=None,
        )

    return SubscriptionResponse(
        id=sub.id,
        plan=sub.plan,
        billing_cycle=sub.billing_cycle.value if sub.billing_cycle else "monthly",
        status=sub.status.value if sub.status else "active",
        amount_cents=sub.amount_cents or 0,
        currency=sub.currency or "usd",
        current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
        cancel_at=sub.cancel_at.isoformat() if sub.cancel_at else None,
        trial_ends_at=sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
    )


@router.post("/subscription/cancel")
async def cancel_subscription(
    at_period_end: bool = True,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel the current subscription."""
    billing = get_billing_service()

    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )
    sub = result.scalar_one_or_none()

    if not sub:
        raise HTTPException(404, "No active subscription found")

    if sub.stripe_subscription_id and billing.is_available:
        billing.cancel_subscription(sub.stripe_subscription_id, at_period_end=at_period_end)

    if at_period_end:
        from datetime import datetime, timezone
        sub.cancel_at = sub.current_period_end
    else:
        sub.status = SubscriptionStatus.CANCELED
        sub.canceled_at = datetime.now(timezone.utc)
        user.plan = PlanTier.FREE

    await db.flush()

    audit = get_audit_logger()
    await audit.log(
        action="subscription_cancel",
        user_id=user.id,
        resource_type="subscription",
        resource_id=sub.id,
        description=f"Subscription canceled (at_period_end={at_period_end})",
        db_session=db,
    )

    return {"message": "Subscription canceled", "at_period_end": at_period_end}


@router.post("/subscription/resume")
async def resume_subscription(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume a subscription that was canceled but hasn't expired yet."""
    billing = get_billing_service()

    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.cancel_at.isnot(None),
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )
    sub = result.scalar_one_or_none()

    if not sub:
        raise HTTPException(404, "No cancelable subscription found")

    if sub.stripe_subscription_id and billing.is_available:
        billing.resume_subscription(sub.stripe_subscription_id)

    sub.cancel_at = None
    await db.flush()

    return {"message": "Subscription resumed"}


# =============================================================================
# Invoices
# =============================================================================

@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's invoices."""
    result = await db.execute(
        select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.created_at.desc()).limit(50)
    )
    invoices = result.scalars().all()

    return [
        InvoiceResponse(
            id=inv.id,
            status=inv.status.value if inv.status else "draft",
            total_cents=inv.total_cents or 0,
            currency=inv.currency or "usd",
            invoice_pdf=inv.invoice_pdf_url,
            created_at=inv.created_at.isoformat() if inv.created_at else "",
        )
        for inv in invoices
    ]


@router.get("/upcoming-invoice")
async def get_upcoming_invoice(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Preview the next upcoming invoice."""
    billing = get_billing_service()
    if not billing.is_available:
        return {"message": "Billing not configured", "upcoming": None}

    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.stripe_customer_id.isnot(None),
        )
    )
    sub = result.scalar_one_or_none()

    if not sub or not sub.stripe_customer_id:
        return {"message": "No subscription found", "upcoming": None}

    upcoming = billing.get_upcoming_invoice(sub.stripe_customer_id)
    return {"upcoming": upcoming}


# =============================================================================
# Stripe Webhooks
# =============================================================================

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events."""
    billing = get_billing_service()

    body = await request.body()

    if stripe_signature and billing.config.webhook_secret:
        event = billing.construct_webhook_event(body, stripe_signature)
        if not event:
            raise HTTPException(400, "Invalid webhook signature")
    else:
        import json
        try:
            event = type("Event", (), json.loads(body))()
        except Exception:
            raise HTTPException(400, "Invalid webhook payload")

    event_type = getattr(event, "type", "") if hasattr(event, "type") else event.get("type", "")
    logger.info(f"Stripe webhook: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(event, db)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(event, db)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(event, db)
        elif event_type == "invoice.paid":
            await _handle_invoice_paid(event, db)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(event, db)
    except Exception as e:
        logger.error(f"Webhook handler error: {e}")

    return {"received": True}


# =============================================================================
# Webhook Handlers
# =============================================================================

async def _handle_checkout_completed(event, db: AsyncSession):
    """Process completed checkout session."""
    data = event.data.object if hasattr(event, "data") else event.get("data", {}).get("object", {})
    
    user_id = data.get("metadata", {}).get("user_id")
    customer_id = data.get("customer")
    subscription_id = data.get("subscription")

    if not user_id or not subscription_id:
        return

    # Create subscription record
    sub = Subscription(
        user_id=user_id,
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
        status=SubscriptionStatus.ACTIVE,
    )
    db.add(sub)

    # Update user plan
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.plan = PlanTier.PRO  # Will be updated by subscription.updated

    await db.flush()
    logger.info(f"Checkout completed for user {user_id}")


async def _handle_subscription_updated(event, db: AsyncSession):
    """Process subscription updates."""
    data = event.data.object if hasattr(event, "data") else event.get("data", {}).get("object", {})
    sub_id = data.get("id")

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == sub_id)
    )
    sub = result.scalar_one_or_none()

    if sub:
        status_map = {
            "active": SubscriptionStatus.ACTIVE,
            "trialing": SubscriptionStatus.TRIALING,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELED,
        }
        sub.status = status_map.get(data.get("status"), SubscriptionStatus.ACTIVE)
        await db.flush()


async def _handle_subscription_deleted(event, db: AsyncSession):
    """Process subscription deletion."""
    data = event.data.object if hasattr(event, "data") else event.get("data", {}).get("object", {})
    sub_id = data.get("id")

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == sub_id)
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub.status = SubscriptionStatus.CANCELED
        
        # Downgrade user to free
        user_result = await db.execute(select(User).where(User.id == sub.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.plan = PlanTier.FREE
        
        await db.flush()


async def _handle_invoice_paid(event, db: AsyncSession):
    """Process paid invoice."""
    data = event.data.object if hasattr(event, "data") else event.get("data", {}).get("object", {})
    logger.info(f"Invoice paid: {data.get('id')}")


async def _handle_payment_failed(event, db: AsyncSession):
    """Process failed payment."""
    data = event.data.object if hasattr(event, "data") else event.get("data", {}).get("object", {})
    logger.warning(f"Payment failed for invoice: {data.get('id')}")
