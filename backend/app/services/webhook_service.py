"""Webhook service for sending notifications about conversion events."""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WebhookConfig(BaseModel):
    """Configuration for a webhook endpoint."""

    id: str
    url: str
    events: List[str]
    secret: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: Optional[datetime] = None
    failure_count: int = 0


class WebhookPayload(BaseModel):
    """Payload sent to webhook endpoints."""

    event: str
    timestamp: datetime
    job_id: Optional[str] = None
    batch_id: Optional[str] = None
    data: Dict[str, Any]
    signature: Optional[str] = None


class WebhookService:
    """Service for managing and sending webhooks."""

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.webhooks: Dict[str, WebhookConfig] = {}
        self._load_webhooks()

    def _load_webhooks(self):
        """Load webhooks from storage."""
        # In production, this would load from database
        # For now, using in-memory storage
        pass

    def _save_webhooks(self):
        """Save webhooks to storage."""
        # In production, this would save to database
        pass

    def create_webhook(
        self, url: str, events: List[str], secret: Optional[str] = None
    ) -> WebhookConfig:
        """Create a new webhook configuration."""
        import uuid

        webhook_id = str(uuid.uuid4())
        config = WebhookConfig(
            id=webhook_id,
            url=url,
            events=events,
            secret=secret,
        )

        self.webhooks[webhook_id] = config
        self._save_webhooks()

        logger.info(f"Created webhook {webhook_id} for URL: {url}")
        return config

    def get_webhook(self, webhook_id: str) -> Optional[WebhookConfig]:
        """Get webhook by ID."""
        return self.webhooks.get(webhook_id)

    def list_webhooks(self, active_only: bool = False) -> List[WebhookConfig]:
        """List all webhooks."""
        webhooks = list(self.webhooks.values())
        if active_only:
            webhooks = [w for w in webhooks if w.active]
        return webhooks

    def update_webhook(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        secret: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> Optional[WebhookConfig]:
        """Update webhook configuration."""
        config = self.webhooks.get(webhook_id)
        if not config:
            return None

        if url is not None:
            config.url = url
        if events is not None:
            config.events = events
        if secret is not None:
            config.secret = secret
        if active is not None:
            config.active = active

        self._save_webhooks()
        logger.info(f"Updated webhook {webhook_id}")
        return config

    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            self._save_webhooks()
            logger.info(f"Deleted webhook {webhook_id}")
            return True
        return False

    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    async def send_webhook(
        self,
        webhook: WebhookConfig,
        event: str,
        data: Dict[str, Any],
        job_id: Optional[str] = None,
        batch_id: Optional[str] = None,
    ) -> bool:
        """Send webhook notification."""
        if not webhook.active:
            return False

        payload = WebhookPayload(
            event=event,
            timestamp=datetime.now(timezone.utc),
            job_id=job_id,
            batch_id=batch_id,
            data=data,
        )

        # Generate signature if secret is configured
        payload_dict = payload.model_dump()
        if webhook.secret:
            payload_str = json.dumps(payload_dict, sort_keys=True, default=str)
            payload_dict["signature"] = self._generate_signature(payload_str, webhook.secret)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Content-Type": "application/json",
                    "X-Webhook-ID": webhook.id,
                    "X-Webhook-Event": event,
                }

                response = await client.post(webhook.url, json=payload_dict, headers=headers)

                success = response.status_code < 400

                if success:
                    webhook.failure_count = 0
                    webhook.last_triggered = datetime.now(timezone.utc)
                    logger.info(f"Webhook {webhook.id} sent successfully")
                else:
                    webhook.failure_count += 1
                    logger.warning(
                        f"Webhook {webhook.id} failed with status {response.status_code}"
                    )

                return success

        except Exception as e:
            webhook.failure_count += 1
            logger.error(f"Failed to send webhook {webhook.id}: {e}")
            return False

    async def trigger_event(
        self,
        event: str,
        data: Dict[str, Any],
        job_id: Optional[str] = None,
        batch_id: Optional[str] = None,
    ):
        """Trigger webhooks for a specific event."""
        webhooks = self.list_webhooks(active_only=True)

        for webhook in webhooks:
            if event in webhook.events:
                # Don't await - fire and forget
                import asyncio

                asyncio.create_task(self.send_webhook(webhook, event, data, job_id, batch_id))

    async def trigger_conversion_started(self, job_id: str, file_id: str, options: Dict[str, Any]):
        """Trigger conversion.started event."""
        await self.trigger_event(
            "conversion.started", {"file_id": file_id, "options": options}, job_id=job_id
        )

    async def trigger_conversion_progress(self, job_id: str, progress: float, stage: str):
        """Trigger conversion.progress event."""
        await self.trigger_event(
            "conversion.progress", {"progress": progress, "stage": stage}, job_id=job_id
        )

    async def trigger_conversion_completed(self, job_id: str, result: Dict[str, Any]):
        """Trigger conversion.completed event."""
        await self.trigger_event("conversion.completed", result, job_id=job_id)

    async def trigger_conversion_failed(self, job_id: str, error: str):
        """Trigger conversion.failed event."""
        await self.trigger_event("conversion.failed", {"error": error}, job_id=job_id)

    async def trigger_batch_completed(self, batch_id: str, results: List[Dict[str, Any]]):
        """Trigger batch.completed event."""
        await self.trigger_event("batch.completed", {"results": results}, batch_id=batch_id)


# Global webhook service instance
_webhook_service: Optional[WebhookService] = None


def get_webhook_service(redis_client=None) -> WebhookService:
    """Get or create global webhook service instance."""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService(redis_client)
    return _webhook_service
