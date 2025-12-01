"""Payment provider HTTP client."""
from dataclasses import dataclass
from typing import Any
from my_app.infrastructure.http_clients.base_client import BaseHTTPClient, ClientConfig

@dataclass
class PaymentResult:
    success: bool
    transaction_id: str | None = None
    error: str | None = None

class PaymentProviderClient(BaseHTTPClient):
    def __init__(self, api_key: str, base_url: str = "https://api.payment.example.com") -> None:
        super().__init__(ClientConfig(base_url=base_url))
        self._api_key = api_key
    
    async def create_charge(self, amount: int, currency: str, source: str) -> PaymentResult:
        try:
            result = await self.post("/charges", {"amount": amount, "currency": currency, "source": source})
            return PaymentResult(success=True, transaction_id=result.get("id"))
        except Exception as e:
            return PaymentResult(success=False, error=str(e))
    
    async def refund(self, charge_id: str, amount: int | None = None) -> PaymentResult:
        try:
            result = await self.post(f"/charges/{charge_id}/refund", {"amount": amount})
            return PaymentResult(success=True, transaction_id=result.get("id"))
        except Exception as e:
            return PaymentResult(success=False, error=str(e))
