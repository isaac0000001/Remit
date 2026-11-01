from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AccountType,
    Customer,
    LedgerAccount,
    LedgerEntry,
    LedgerStatus,
    LedgerTransaction,
    EntryDirection,
    Wallet,
    WalletStatus,
)


class LedgerService:

    @staticmethod
    async def create_customer_wallet(
        db: AsyncSession,
        customer: Customer,
        currency: str,
    ):

        currency = currency.upper()

        if len(currency) != 3 or not currency.isalpha():
            raise HTTPException(
                status_code=400,
                detail="Invalid currency",
            )

        async with db.begin():

            customer_result = await db.execute(
                select(Customer)
                .where(Customer.id == customer.id)
                .with_for_update()
            )

            locked_customer = customer_result.scalar_one_or_none()

            if not locked_customer:
                raise HTTPException(
                    status_code=404,
                    detail="Customer not found",
                )

            if locked_customer.status.value != "active":
                raise HTTPException(
                    status_code=403,
                    detail="Customer account is not active",
                )

            existing = await db.execute(
                select(Wallet).where(
                    Wallet.customer_id == customer.id,
                    Wallet.currency == currency,
                )
            )

            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=409,
                    detail="Wallet already exists",
                )

            wallet = Wallet(
                customer_id=customer.id,
                currency=currency,
                status=WalletStatus.ACTIVE,
            )

            db.add(wallet)

            await db.flush()

            account = LedgerAccount(
                account_code=f"WALLET:{wallet.id}",
                account_type=AccountType.CUSTOMER_WALLET,
                customer_id=customer.id,
                wallet_id=wallet.id,
                currency=currency,
                is_active=True,
            )

            db.add(account)

            await db.flush()

        return wallet

    @staticmethod
    async def post_transaction(
        db: AsyncSession,
        reference: str,
        entries: list[dict],
    ):

        if not reference or len(reference) > 100:
            raise HTTPException(
                status_code=400,
                detail="Invalid ledger reference",
            )

        if len(entries) < 2:
            raise HTTPException(
                status_code=400,
                detail="A ledger transaction requires at least two entries",
            )

        totals = defaultdict(
            lambda: {
                "debit": Decimal("0"),
                "credit": Decimal("0"),
            }
        )

        account_ids = set()

        for entry in entries:

            account_id = entry["account_id"]
            amount = Decimal(str(entry["amount"]))
            direction = entry["direction"]
            currency = entry["currency"].upper()

            if amount <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Ledger amounts must be positive",
                )

            if direction not in ("debit", "credit"):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid ledger direction",
                )

            if len(currency) != 3 or not currency.isalpha():
                raise HTTPException(
                    status_code=400,
                    detail="Invalid ledger currency",
                )

            account_ids.add(account_id)

            totals[currency][direction] += amount

        for currency, amounts in totals.items():

            if amounts["debit"] != amounts["credit"]:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unbalanced ledger transaction for {currency}"
                    ),
                )

        async with db.begin():

            existing = await db.execute(
                select(LedgerTransaction)
                .where(LedgerTransaction.reference == reference)
                .with_for_update()
            )

            existing_transaction = existing.scalar_one_or_none()

            if existing_transaction:

                if existing_transaction.status == LedgerStatus.POSTED:
                    return existing_transaction

                raise HTTPException(
                    status_code=409,
                    detail="Ledger reference already exists",
                )

            locked_accounts = await db.execute(
                select(LedgerAccount)
                .where(LedgerAccount.id.in_(account_ids))
                .order_by(LedgerAccount.id)
                .with_for_update()
            )

            accounts = {
                account.id: account
                for account in locked_accounts.scalars().all()
            }

            if len(accounts) != len(account_ids):
                raise HTTPException(
                    status_code=404,
                    detail="One or more ledger accounts do not exist",
                )

            for entry in entries:

                account = accounts[entry["account_id"]]

                if not account.is_active:
                    raise HTTPException(
                        status_code=403,
                        detail="Ledger account is inactive",
                    )

                if account.currency != entry["currency"].upper():
                    raise HTTPException(
                        status_code=400,
                        detail="Ledger currency does not match account currency",
                    )

            transaction = LedgerTransaction(
                reference=reference,
                status=LedgerStatus.PENDING,
            )

            db.add(transaction)

            await db.flush()

            for entry in entries:

                ledger_entry = LedgerEntry(
                    ledger_transaction_id=transaction.id,
                    ledger_account_id=entry["account_id"],
                    direction=EntryDirection(entry["direction"]),
                    amount=Decimal(str(entry["amount"])),
                    currency=entry["currency"].upper(),
                )

                db.add(ledger_entry)

            transaction.status = LedgerStatus.POSTED

            await db.flush()

        return transaction

    @staticmethod
    async def get_wallet_balance(
        db: AsyncSession,
        customer_id: UUID,
        wallet_id: UUID,
    ):

        wallet_result = await db.execute(
            select(Wallet).where(
                Wallet.id == wallet_id,
                Wallet.customer_id == customer_id,
            )
        )

        wallet = wallet_result.scalar_one_or_none()

        if not wallet:
            raise HTTPException(
                status_code=404,
                detail="Wallet not found",
            )

        account_result = await db.execute(
            select(LedgerAccount).where(
                LedgerAccount.wallet_id == wallet.id
            )
        )

        account = account_result.scalar_one_or_none()

        if not account:
            raise HTTPException(
                status_code=404,
                detail="Ledger account not found",
            )

        entries_result = await db.execute(
            select(LedgerEntry).where(
                LedgerEntry.ledger_account_id == account.id
            )
        )

        balance = Decimal("0")

        for entry in entries_result.scalars().all():

            transaction_result = await db.execute(
                select(LedgerTransaction).where(
                    LedgerTransaction.id == entry.ledger_transaction_id,
                    LedgerTransaction.status == LedgerStatus.POSTED,
                )
            )

            if transaction_result.scalar_one_or_none():

                if entry.direction == EntryDirection.CREDIT:
                    balance += entry.amount
                else:
                    balance -= entry.amount

        return {
            "wallet_id": str(wallet.id),
            "currency": wallet.currency,
            "balance": balance,
            "status": wallet.status.value,
        }
