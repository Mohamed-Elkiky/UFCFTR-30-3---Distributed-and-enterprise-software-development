import uuid

from apps.payments.gateways.base import BaseGateway
from apps.payments.models import PaymentTransaction


class MockGateway(BaseGateway):
    """Mock payment gateway for testing (TC-007). Always succeeds."""

    def initiate(self, amount_pence: int, order_id) -> dict:
        ref = f"MOCK-{uuid.uuid4()}"
        PaymentTransaction.objects.create(
            customer_order_id=order_id,
            amount_pence=amount_pence,
            provider='mock',
            provider_ref=ref,
            status=PaymentTransaction.Status.AUTHORISED,
        )
        return {"ref": ref, "status": "authorised"}

    def capture(self, transaction_ref: str) -> dict:
        PaymentTransaction.objects.filter(
            provider_ref=transaction_ref
        ).update(status=PaymentTransaction.Status.CAPTURED)
        return {"status": "captured"}
