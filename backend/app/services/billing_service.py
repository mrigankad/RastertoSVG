"""Billing & Subscription service — Phase 12.

Stripe integration for:
- Customer creation
- Checkout session generation
- Subscription management (upgrade/downgrade/cancel)
- Webhook processing
- Invoice retrieval
- Usage-based metering
"""

import hashlib
import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Stripe Configuration
# =============================================================================

class StripeConfig:
    """Stripe configuration from environment."""
    def __init__(self):
        self.secret_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.success_url = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/billing/success")
        self.cancel_url = os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/billing/cancel")
        self.portal_return_url = os.getenv("STRIPE_PORTAL_URL", "http://localhost:3000/dashboard")


_stripe_config = StripeConfig()


# =============================================================================
# Billing Service
# =============================================================================

class BillingService:
    """Stripe-powered billing and subscription management."""

    def __init__(self, config: Optional[StripeConfig] = None):
        self.config = config or _stripe_config
        self._stripe = None

    def _get_stripe(self):
        """Lazy-load Stripe SDK."""
        if self._stripe is None:
            try:
                import stripe
                stripe.api_key = self.config.secret_key
                self._stripe = stripe
                logger.info("Stripe SDK initialized")
            except ImportError:
                logger.warning("stripe package not installed — billing disabled")
        return self._stripe

    @property
    def is_available(self) -> bool:
        """Check if Stripe is configured and available."""
        return bool(self.config.secret_key) and self._get_stripe() is not None

    # =========================================================================
    # Customers
    # =========================================================================

    def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[str]:
        """Create a Stripe customer. Returns customer ID."""
        stripe = self._get_stripe()
        if not stripe:
            return None

        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id or ""},
            )
            logger.info(f"Stripe customer created: {customer.id} for {email}")
            return customer.id
        except Exception as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            return None

    def get_customer(self, customer_id: str) -> Optional[Dict]:
        """Get Stripe customer details."""
        stripe = self._get_stripe()
        if not stripe:
            return None

        try:
            return stripe.Customer.retrieve(customer_id)
        except Exception as e:
            logger.error(f"Failed to get customer {customer_id}: {e}")
            return None

    # =========================================================================
    # Checkout Sessions
    # =========================================================================

    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        user_id: str,
        mode: str = "subscription",
        trial_days: Optional[int] = None,
    ) -> Optional[Dict[str, str]]:
        """Create a Stripe Checkout session.
        
        Returns:
            {"session_id": str, "url": str}
        """
        stripe = self._get_stripe()
        if not stripe:
            return None

        try:
            params = {
                "customer": customer_id,
                "payment_method_types": ["card"],
                "line_items": [{"price": price_id, "quantity": 1}],
                "mode": mode,
                "success_url": f"{self.config.success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                "cancel_url": self.config.cancel_url,
                "metadata": {"user_id": user_id},
                "allow_promotion_codes": True,
            }

            if trial_days and mode == "subscription":
                params["subscription_data"] = {
                    "trial_period_days": trial_days,
                }

            session = stripe.checkout.Session.create(**params)

            return {
                "session_id": session.id,
                "url": session.url,
            }

        except Exception as e:
            logger.error(f"Failed to create checkout session: {e}")
            return None

    # =========================================================================
    # Subscriptions
    # =========================================================================

    def get_subscription(self, subscription_id: str) -> Optional[Dict]:
        """Get Stripe subscription details."""
        stripe = self._get_stripe()
        if not stripe:
            return None

        try:
            return stripe.Subscription.retrieve(subscription_id)
        except Exception as e:
            logger.error(f"Failed to get subscription {subscription_id}: {e}")
            return None

    def update_subscription(
        self,
        subscription_id: str,
        new_price_id: str,
        proration_behavior: str = "create_prorations",
    ) -> Optional[Dict]:
        """Update (upgrade/downgrade) a subscription."""
        stripe = self._get_stripe()
        if not stripe:
            return None

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            updated = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    "id": subscription["items"]["data"][0].id,
                    "price": new_price_id,
                }],
                proration_behavior=proration_behavior,
            )
            logger.info(f"Subscription updated: {subscription_id} → {new_price_id}")
            return updated
        except Exception as e:
            logger.error(f"Failed to update subscription: {e}")
            return None

    def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True,
    ) -> Optional[Dict]:
        """Cancel a subscription (immediately or at period end)."""
        stripe = self._get_stripe()
        if not stripe:
            return None

        try:
            if at_period_end:
                result = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                result = stripe.Subscription.delete(subscription_id)

            logger.info(f"Subscription canceled: {subscription_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return None

    def resume_subscription(self, subscription_id: str) -> Optional[Dict]:
        """Resume a canceled-at-period-end subscription."""
        stripe = self._get_stripe()
        if not stripe:
            return None

        try:
            result = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=False,
            )
            return result
        except Exception as e:
            logger.error(f"Failed to resume subscription: {e}")
            return None

    # =========================================================================
    # Customer Portal
    # =========================================================================

    def create_portal_session(self, customer_id: str) -> Optional[str]:
        """Create a Stripe Customer Portal session URL."""
        stripe = self._get_stripe()
        if not stripe:
            return None

        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=self.config.portal_return_url,
            )
            return session.url
        except Exception as e:
            logger.error(f"Failed to create portal session: {e}")
            return None

    # =========================================================================
    # Invoices
    # =========================================================================

    def list_invoices(
        self,
        customer_id: str,
        limit: int = 20,
    ) -> List[Dict]:
        """List customer invoices."""
        stripe = self._get_stripe()
        if not stripe:
            return []

        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit,
            )
            return [
                {
                    "id": inv.id,
                    "status": inv.status,
                    "total": inv.total,
                    "currency": inv.currency,
                    "invoice_pdf": inv.invoice_pdf,
                    "hosted_invoice_url": inv.hosted_invoice_url,
                    "created": inv.created,
                    "paid_at": inv.status_transitions.get("paid_at") if inv.status_transitions else None,
                }
                for inv in invoices.data
            ]
        except Exception as e:
            logger.error(f"Failed to list invoices: {e}")
            return []

    def get_upcoming_invoice(self, customer_id: str) -> Optional[Dict]:
        """Get the next upcoming invoice."""
        stripe = self._get_stripe()
        if not stripe:
            return None

        try:
            invoice = stripe.Invoice.upcoming(customer=customer_id)
            return {
                "total": invoice.total,
                "currency": invoice.currency,
                "period_start": invoice.period_start,
                "period_end": invoice.period_end,
                "lines": [
                    {
                        "description": line.description,
                        "amount": line.amount,
                    }
                    for line in invoice.lines.data
                ],
            }
        except Exception as e:
            logger.error(f"Failed to get upcoming invoice: {e}")
            return None

    # =========================================================================
    # Usage Metering
    # =========================================================================

    def report_usage(
        self,
        subscription_item_id: str,
        quantity: int,
        timestamp: Optional[int] = None,
    ) -> bool:
        """Report metered usage to Stripe."""
        stripe = self._get_stripe()
        if not stripe:
            return False

        try:
            stripe.SubscriptionItem.create_usage_record(
                subscription_item_id,
                quantity=quantity,
                timestamp=timestamp or int(time.time()),
                action="increment",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to report usage: {e}")
            return False

    # =========================================================================
    # Webhook Processing
    # =========================================================================

    def construct_webhook_event(
        self,
        payload: bytes,
        sig_header: str,
    ) -> Optional[Any]:
        """Verify and construct a Stripe webhook event."""
        stripe = self._get_stripe()
        if not stripe:
            return None

        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                self.config.webhook_secret,
            )
            return event
        except Exception as e:
            logger.error(f"Webhook verification failed: {e}")
            return None


# =============================================================================
# License Key Service
# =============================================================================

class LicenseService:
    """License key generation and validation for self-hosted deployments."""

    PREFIX = "RSVG-"

    @staticmethod
    def generate_license_key() -> tuple[str, str, str]:
        """Generate a license key.
        
        Returns: (full_key, key_prefix, key_hash)
        """
        segments = [secrets.token_hex(4).upper() for _ in range(4)]
        full_key = f"RSVG-{'-'.join(segments)}"
        key_prefix = full_key[:16]
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        return full_key, key_prefix, key_hash

    @staticmethod
    def validate_key_format(key: str) -> bool:
        """Validate license key format."""
        import re
        return bool(re.match(r"^RSVG-[A-F0-9]{8}-[A-F0-9]{8}-[A-F0-9]{8}-[A-F0-9]{8}$", key))

    @staticmethod
    def hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()


# =============================================================================
# Audit Logger
# =============================================================================

class AuditLogger:
    """Log user actions for compliance and analytics."""

    def __init__(self):
        self._buffer: List[Dict] = []
        self._buffer_size = 50

    async def log(
        self,
        action: str,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        db_session=None,
    ):
        """Log an audit event."""
        from app.models.billing import AuditLog, AuditAction

        try:
            audit_action = AuditAction(action)
        except ValueError:
            logger.warning(f"Unknown audit action: {action}")
            return

        entry = AuditLog(
            user_id=user_id,
            team_id=team_id,
            action=audit_action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            metadata_json=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if db_session:
            db_session.add(entry)
            await db_session.flush()
        else:
            # Buffer for batch insert
            self._buffer.append({
                "user_id": user_id,
                "team_id": team_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "description": description,
                "metadata": metadata,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        logger.debug(f"Audit: {action} by user={user_id} on {resource_type}/{resource_id}")

    async def flush_buffer(self, db_session):
        """Flush buffered audit entries to the database."""
        from app.models.billing import AuditLog, AuditAction

        if not self._buffer:
            return

        for entry_data in self._buffer:
            try:
                entry = AuditLog(
                    user_id=entry_data.get("user_id"),
                    team_id=entry_data.get("team_id"),
                    action=AuditAction(entry_data["action"]),
                    resource_type=entry_data.get("resource_type"),
                    resource_id=entry_data.get("resource_id"),
                    description=entry_data.get("description"),
                    metadata_json=entry_data.get("metadata", {}),
                    ip_address=entry_data.get("ip_address"),
                    user_agent=entry_data.get("user_agent"),
                )
                db_session.add(entry)
            except Exception as e:
                logger.warning(f"Failed to flush audit entry: {e}")

        await db_session.flush()
        self._buffer.clear()


# =============================================================================
# Singletons
# =============================================================================

_billing: Optional[BillingService] = None
_audit: Optional[AuditLogger] = None
_license: Optional[LicenseService] = None


def get_billing_service() -> BillingService:
    global _billing
    if _billing is None:
        _billing = BillingService()
    return _billing


def get_audit_logger() -> AuditLogger:
    global _audit
    if _audit is None:
        _audit = AuditLogger()
    return _audit


def get_license_service() -> LicenseService:
    global _license
    if _license is None:
        _license = LicenseService()
    return _license
