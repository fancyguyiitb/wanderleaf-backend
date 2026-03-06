from decimal import Decimal

from django.db import models

from apps.common.models import TimeStampedModel


class Payment(TimeStampedModel):
    """
    Tracks payment transactions for bookings.
    
    This is a placeholder implementation. Full payment gateway integration
    (Stripe, Razorpay, etc.) will be added later.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Credit/Debit Card"
        UPI = "upi", "UPI"
        NET_BANKING = "net_banking", "Net Banking"
        WALLET = "wallet", "Wallet"
        PLACEHOLDER = "placeholder", "Placeholder (Test)"

    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True,
        help_text="The booking this payment is for.",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Payment amount.",
    )
    currency = models.CharField(
        max_length=3,
        default="INR",
        help_text="Currency code (ISO 4217). INR for Razorpay.",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.PLACEHOLDER,
    )

    gateway_order_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Order/Intent ID from payment gateway.",
    )
    gateway_payment_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Payment ID from payment gateway after completion.",
    )
    gateway_signature = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Signature from payment gateway for verification.",
    )

    failure_reason = models.TextField(
        blank=True,
        default="",
        help_text="Reason for payment failure (if applicable).",
    )

    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Amount refunded (if any).",
    )
    refunded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when refund was processed.",
    )
    gateway_refund_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Refund ID from payment gateway (e.g. Razorpay rfnd_xxx).",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata from payment gateway.",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["booking", "status"]),
            models.Index(fields=["gateway_order_id"]),
        ]

    def __str__(self):
        return f"Payment {self.id} - {self.amount} {self.currency} ({self.status})"

    @property
    def is_successful(self) -> bool:
        return self.status == self.Status.COMPLETED

    @property
    def can_be_refunded(self) -> bool:
        return self.status == self.Status.COMPLETED and self.refund_amount < self.amount
