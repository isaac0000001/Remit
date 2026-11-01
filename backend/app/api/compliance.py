from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_customer
from app.compliance_models import (
    AMLStatus,
    KYCRecord,
    KYCStatus,
)
from app.compliance_schemas import (
    KYCResponse,
    KYCSubmission,
)
from app.database import get_db
from app.models import Customer


router = APIRouter(
    prefix="/compliance",
    tags=["Compliance"],
)


@router.post(
    "/kyc",
    response_model=KYCResponse,
    status_code=201,
)
async def submit_kyc(
    data: KYCSubmission,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    if data.date_of_birth >= date.today():
        raise HTTPException(
            status_code=400,
            detail="Invalid date of birth",
        )

    existing = await db.execute(
        select(KYCRecord).where(
            KYCRecord.customer_id == customer.id
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="A KYC record already exists for this customer",
        )

    record = KYCRecord(
        customer_id=customer.id,
        date_of_birth=data.date_of_birth,
        nationality=data.nationality.upper(),
        residential_country=data.residential_country.upper(),
        residential_address=data.residential_address,
        document_type=data.document_type,
        document_reference=data.document_reference,
        status=KYCStatus.PENDING,
        aml_status=AMLStatus.NOT_STARTED,
    )

    db.add(record)

    await db.commit()
    await db.refresh(record)

    return record


@router.get(
    "/kyc/me",
    response_model=KYCResponse,
)
async def get_my_kyc(
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KYCRecord).where(
            KYCRecord.customer_id == customer.id
        )
    )

    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="No KYC application found",
        )

    return record
