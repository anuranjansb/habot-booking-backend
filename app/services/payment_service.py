import logging
import os

import requests


logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    """Raised when the mock payment gateway cannot be reached."""


def verify_payment(event_id, booking_id, payment_status):
    gateway_url = os.getenv(
        "PAYMENT_GATEWAY_URL",
        "https://mock-payment-gateway.example.com/verify",
    )

    payload = {
        "event_id": event_id,
        "booking_id": booking_id,
        "status": payment_status,
    }

    try:
        response = requests.post(
            gateway_url,
            json=payload,
            timeout=5,
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("verified"):
            logger.warning(
                "Payment verification failed for event_id=%s",
                event_id,
            )
            return False

        logger.info(
            "Payment verified successfully for event_id=%s",
            event_id,
        )

        return True

    except requests.RequestException as exc:
        logger.exception(
            "Payment gateway request failed for event_id=%s",
            event_id,
        )
        raise PaymentGatewayError(
            "Payment gateway unavailable"
        ) from exc

    except ValueError as exc:
        logger.exception(
            "Invalid response from payment gateway for event_id=%s",
            event_id,
        )
        raise PaymentGatewayError(
            "Invalid payment gateway response"
        ) from exc
