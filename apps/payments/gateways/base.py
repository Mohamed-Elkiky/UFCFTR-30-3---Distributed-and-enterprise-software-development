from abc import ABC, abstractmethod


class BaseGateway(ABC):
    """Abstract base class for payment gateways (TC-007)."""

    @abstractmethod
    def initiate(self, amount_pence: int, order_id) -> dict:
        """
        Authorise a payment.

        Args:
            amount_pence: Amount to charge in pence.
            order_id: The order identifier.

        Returns:
            dict with at least 'ref' (str) and 'status' (str).
        """

    @abstractmethod
    def capture(self, transaction_ref: str) -> dict:
        """
        Capture a previously authorised payment.

        Args:
            transaction_ref: The reference returned by initiate().

        Returns:
            dict with at least 'status' (str).
        """
