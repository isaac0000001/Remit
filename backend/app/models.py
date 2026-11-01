import enum
import uuid

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid


class Base(DeclarativeBase):
    pass


def utc_now():
    return datetime.now(timezone.utc)


class CustomerStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class WalletStatus(str, enum.Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class TransferStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LedgerStatus(str, enum.Enum):
    PENDING = "pending"
    POSTED = "posted"
    REVERSED = "reversed"


class EntryDirection(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    phone_number: Mapped[str | None] = mapped_column(
        String(30), unique=True, nullable=True
    )

    country: Mapped[str] = mapped_column(String(2), nullable=False)

    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus, native_enum=False),
        default=CustomerStatus.PENDING,
        nullable=False,
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class Wallet(Base):
    __tablename__ = "wallets"

    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "currency",
            name="uq_wallet_customer_currency",
        ),
        CheckConstraint(
            "length(currency) = 3",
            name="ck_wallet_currency_length",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False, index=True
    )

    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    status: Mapped[WalletStatus] = mapped_column(
        Enum(WalletStatus, native_enum=False),
        default=WalletStatus.ACTIVE,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class RemittanceTransfer(Base):
    __tablename__ = "transfers"

    __table_args__ = (
        CheckConstraint(
            "source_amount > 0",
            name="ck_transfer_source_amount_positive",
        ),
        CheckConstraint(
            "destination_amount > 0",
            name="ck_transfer_destination_amount_positive",
        ),
        CheckConstraint(
            "fee_amount >= 0",
            name="ck_transfer_fee_nonnegative",
        ),
        UniqueConstraint(
            "customer_id",
            "idempotency_key",
            name="uq_transfer_idempotency",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False, index=True
    )

    source_currency: Mapped[str] = mapped_column(
        String(3), nullable=False
    )

    destination_currency: Mapped[str] = mapped_column(
        String(3), nullable=False
    )

    source_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False
    )

    destination_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False
    )

    fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("0"), nullable=False
    )

    exchange_rate: Mapped[Decimal] = mapped_column(
        Numeric(24, 12), nullable=False
    )

    beneficiary_name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )

    beneficiary_account: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    beneficiary_country: Mapped[str] = mapped_column(
        String(2), nullable=False
    )

    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, native_enum=False),
        default=TransferStatus.PENDING,
        nullable=False,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    transfer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transfers.id"), nullable=True, index=True
    )

    reference: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )

    status: Mapped[LedgerStatus] = mapped_column(
        Enum(LedgerStatus, native_enum=False),
        default=LedgerStatus.PENDING,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_ledger_entry_amount_positive",
        ),
        Index(
            "ix_ledger_entries_wallet_created",
            "wallet_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    ledger_transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ledger_transactions.id"), nullable=False, index=True
    )

    wallet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wallets.id"), nullable=False, index=True
    )

    direction: Mapped[EntryDirection] = mapped_column(
        Enum(EntryDirection, native_enum=False),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False
    )

    currency: Mapped[str] = mapped_column(
        String(3), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
