import enum
import uuid

from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.models import Base


def utc_now():
    return datetime.now(timezone.utc)


class KYCStatus(str, enum.Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    MORE_INFORMATION_REQUIRED = "more_information_required"


class AMLStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    CLEAR = "clear"
    FLAGGED = "flagged"
    MANUAL_REVIEW = "manual_review"


class IdentityDocumentType(str, enum.Enum):
    PASSPORT = "passport"
    NATIONAL_ID = "national_id"
    DRIVERS_LICENSE = "drivers_license"
    RESIDENCE_PERMIT = "residence_permit"


class KYCRecord(Base):
    __tablename__ = "kyc_records"

    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            name="uq_kyc_customer",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False,
        index=True,
    )

    date_of_birth: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    nationality: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    residential_country: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    residential_address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    document_type: Mapped[IdentityDocumentType] = mapped_column(
        Enum(IdentityDocumentType, native_enum=False),
        nullable=False,
    )

    document_reference: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    status: Mapped[KYCStatus] = mapped_column(
        Enum(KYCStatus, native_enum=False),
        default=KYCStatus.PENDING,
        nullable=False,
    )

    aml_status: Mapped[AMLStatus] = mapped_column(
        Enum(AMLStatus, native_enum=False),
        default=AMLStatus.NOT_STARTED,
        nullable=False,
    )

    review_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
