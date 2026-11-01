from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.compliance_models import (
    AMLStatus,
    IdentityDocumentType,
    KYCStatus,
)


class KYCSubmission(BaseModel):
    date_of_birth: date

    nationality: str = Field(
        min_length=2,
        max_length=2,
    )

    residential_country: str = Field(
        min_length=2,
        max_length=2,
    )

    residential_address: str = Field(
        min_length=5,
        max_length=500,
    )

    document_type: IdentityDocumentType

    document_reference: str | None = Field(
        default=None,
        max_length=150,
    )


class KYCResponse(BaseModel):
    id: UUID
    customer_id: UUID
    date_of_birth: date
    nationality: str
    residential_country: str
    document_type: IdentityDocumentType
    status: KYCStatus
    aml_status: AMLStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
