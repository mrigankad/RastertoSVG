"""Billing & Subscription models — Phase 12.

SQLAlchemy ORM models for:
- Subscriptions (plan, billing cycle, status)
- Invoices (line items, amounts, payment status)
- Payment methods (cards, via Stripe)
- Audit log (action tracking for compliance)
- License keys (self-hosted/white-label)
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Boolean, Column, DateTime, Float,
    ForeignKey, Integer, String, Text, BigInteger, JSON,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SAEnum

from app.models.database import Base


# =============================================================================
# Enums
# =============================================================================

class SubscriptionStatus(str, Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    PAUSED = "paused"
    CANCELED = "canceled"
    EXPIRED = "expired"


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class AuditAction(str, Enum):
    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_RESET = "password_reset"
    
    # Account
    PLAN_UPGRADE = "plan_upgrade"
    PLAN_DOWNGRADE = "plan_downgrade"
    SUBSCRIPTION_CANCEL = "subscription_cancel"
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"
    
    # Team
    TEAM_CREATE = "team_create"
    TEAM_MEMBER_ADD = "team_member_add"
    TEAM_MEMBER_REMOVE = "team_member_remove"
    TEAM_ROLE_CHANGE = "team_role_change"
    
    # Data
    PROJECT_CREATE = "project_create"
    PROJECT_DELETE = "project_delete"
    CONVERSION_START = "conversion_start"
    CONVERSION_COMPLETE = "conversion_complete"
    FILE_UPLOAD = "file_upload"
    FILE_DELETE = "file_delete"
    
    # Admin
    ADMIN_USER_BAN = "admin_user_ban"
    ADMIN_USER_UNBAN = "admin_user_unban"
    ADMIN_PLAN_OVERRIDE = "admin_plan_override"
    ADMIN_CONFIG_CHANGE = "admin_config_change"
    
    # Plugin
    PLUGIN_INSTALL = "plugin_install"
    PLUGIN_UNINSTALL = "plugin_uninstall"


class LicenseType(str, Enum):
    SELF_HOSTED = "self_hosted"
    WHITE_LABEL = "white_label"
    OEM = "oem"


# =============================================================================
# Subscription Model
# =============================================================================

class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_user", "user_id"),
        Index("ix_subscriptions_stripe", "stripe_subscription_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    # Plan
    plan = Column(String(50), nullable=False, default="free")
    billing_cycle = Column(SAEnum(BillingCycle), default=BillingCycle.MONTHLY)
    status = Column(SAEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)

    # Stripe
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)
    stripe_price_id = Column(String(255), nullable=True)

    # Billing
    amount_cents = Column(Integer, default=0)  # Monthly price in cents
    currency = Column(String(3), default="usd")
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")


# =============================================================================
# Invoice Model
# =============================================================================

class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_user", "user_id"),
        Index("ix_invoices_stripe", "stripe_invoice_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Stripe
    stripe_invoice_id = Column(String(255), nullable=True, unique=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)

    # Amounts
    subtotal_cents = Column(Integer, default=0)
    tax_cents = Column(Integer, default=0)
    total_cents = Column(Integer, default=0)
    amount_paid_cents = Column(Integer, default=0)
    currency = Column(String(3), default="usd")

    # Status
    status = Column(SAEnum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    description = Column(Text, nullable=True)

    # Line items
    line_items = Column(JSON, default=list)
    # Example: [{"description": "Pro Plan (Monthly)", "amount": 999, "quantity": 1}]

    # Dates
    invoice_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    due_date = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Download
    invoice_pdf_url = Column(String(512), nullable=True)
    receipt_url = Column(String(512), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")
    user = relationship("User", backref="invoices")


# =============================================================================
# Audit Log
# =============================================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_user", "user_id"),
        Index("ix_audit_action", "action"),
        Index("ix_audit_created", "created_at"),
        Index("ix_audit_team", "team_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    team_id = Column(String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    action = Column(SAEnum(AuditAction), nullable=False)
    resource_type = Column(String(100), nullable=True)  # "user", "project", "conversion"
    resource_id = Column(String(36), nullable=True)
    description = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)

    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    request_id = Column(String(36), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="audit_logs")


# =============================================================================
# License Key (Self-Hosted / White-Label)
# =============================================================================

class LicenseKey(Base):
    __tablename__ = "license_keys"
    __table_args__ = (
        Index("ix_license_key", "key_hash", unique=True),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    license_type = Column(SAEnum(LicenseType), nullable=False)
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(16), nullable=False)

    # License details
    organization = Column(String(255), nullable=True)
    max_users = Column(Integer, default=1)
    features = Column(JSON, default=list)  # Enabled feature flags
    custom_branding = Column(JSON, default=dict)  # White-label settings

    # Validity
    is_active = Column(Boolean, default=True)
    issued_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_validated_at = Column(DateTime(timezone=True), nullable=True)

    # Usage
    activations = Column(Integer, default=0)
    max_activations = Column(Integer, default=3)

    user = relationship("User", backref="license_keys")


# =============================================================================
# Pricing constants
# =============================================================================

PRICING = {
    "free": {
        "monthly_cents": 0,
        "yearly_cents": 0,
        "stripe_price_monthly": None,
        "stripe_price_yearly": None,
        "name": "Free",
    },
    "pro": {
        "monthly_cents": 999,
        "yearly_cents": 9588,  # $7.99/mo billed yearly
        "stripe_price_monthly": "price_pro_monthly",
        "stripe_price_yearly": "price_pro_yearly",
        "name": "Pro",
    },
    "team": {
        "monthly_cents": 2999,
        "yearly_cents": 28788,  # $23.99/mo billed yearly
        "stripe_price_monthly": "price_team_monthly",
        "stripe_price_yearly": "price_team_yearly",
        "name": "Team",
    },
    "enterprise": {
        "monthly_cents": 9999,
        "yearly_cents": 95988,  # $79.99/mo billed yearly
        "stripe_price_monthly": "price_enterprise_monthly",
        "stripe_price_yearly": "price_enterprise_yearly",
        "name": "Enterprise",
    },
}
