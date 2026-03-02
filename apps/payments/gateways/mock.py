import uuid

from apps.payments.gateways.base import BaseGateway
from apps.payments.models import PaymentTransaction


class MockGateway(BaseGateway):
    """Mock payment gateway for testing (TC-007). Always succeeds."""

    def initiate(self, amount_pence: int, order_id) -> dict:
        ref = f"MOCK-{uuid.uuid4()}"
        PaymentTransaction.objects.create(
            order_id=order_id,
            amount_pence=amount_pence,
            payment_method=PaymentTransaction.PaymentMethod.MOCK,
            status=PaymentTransaction.Status.PENDING,
            external_reference=ref,
        )
        return {"ref": ref, "status": "authorised"}

    def capture(self, transaction_ref: str) -> dict:
        PaymentTransaction.objects.filter(
            external_reference=transaction_ref
        ).update(status=PaymentTransaction.Status.COMPLETED)
        return {"status": "captured"}
