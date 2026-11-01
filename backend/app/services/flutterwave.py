import httpx

from decimal import Decimal

from app.config import settings


class FlutterwaveError(Exception):
    pass


class FlutterwaveService:

    def __init__(self):

        if not settings.FLW_SECRET_KEY:
            raise FlutterwaveError(
                "Flutterwave API key is not configured"
            )

        self.secret_key = (
            settings.FLW_SECRET_KEY.get_secret_value()
        )

        self.base_url = settings.FLW_BASE_URL.rstrip("/")

    async def create_payment(
        self,
        tx_ref: str,
        amount: Decimal,
        currency: str,
        email: str,
        name: str,
        phone_number: str | None = None,
    ):

        if not settings.FLW_REDIRECT_URL:
            raise FlutterwaveError(
                "Flutterwave redirect URL is not configured"
            )

        payload = {
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": currency,
            "redirect_url": settings.FLW_REDIRECT_URL,
            "customer": {
                "email": email,
                "name": name,
                "phonenumber": phone_number or "",
            },
            "customizations": {
                "title": "Remit",
                "description": "Remit payment",
            },
        }

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.post(
                f"{self.base_url}/payments",
                json=payload,
                headers=headers,
            )

            response.raise_for_status()

            result = response.json()

        if result.get("status") != "success":
            raise FlutterwaveError(
                "Flutterwave could not initialize payment"
            )

        checkout_url = result.get("data", {}).get("link")

        if not checkout_url or not checkout_url.startswith(
            "https://checkout.flutterwave.com/"
        ):
            raise FlutterwaveError(
                "Invalid Flutterwave checkout response"
            )

        return checkout_url

    async def verify_payment(self, transaction_id: str):

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.get(
                f"{self.base_url}/transactions/"
                f"{transaction_id}/verify",
                headers=headers,
            )

            response.raise_for_status()

            result = response.json()

        if result.get("status") != "success":
            raise FlutterwaveError(
                "Payment verification failed"
            )

        return result.get("data", {})
