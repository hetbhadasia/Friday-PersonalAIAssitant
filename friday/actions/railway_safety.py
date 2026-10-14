"""
F.R.I.D.A.Y. V3 — Indian Railway Compliance & Safety Protocol
=============================================================
Strict compliance guards for Indian railway and Tatkal reservation workflows.
Explicitly rejects any unauthorized scraping, CAPTCHA bypass, or OTP interception.
"""

from typing import Any
from friday.core.logging import get_logger

logger = get_logger("railway_compliance")


class RailwayComplianceGuard:
    """Enforces ethical and legal boundaries for railway operations."""

    @staticmethod
    def assert_compliance_rules(request_params: dict[str, Any]) -> None:
        """
        Validates that request does not attempt unauthorized bypasses:
        1. No automated CAPTCHA solving
        2. No unauthorized session interception
        3. No OTP automation or credential hijacking
        """
        # Checks for illegal automation flags
        forbidden_flags = ["bypass_captcha", "intercept_otp", "scrape_irctc_direct", "bot_queue_bypass"]
        for flag in forbidden_flags:
            if request_params.get(flag):
                logger.error("Blocked prohibited railway action: %s", flag)
                raise SecurityError(
                    f"Compliance violation: '{flag}' is strictly prohibited. F.R.I.D.A.Y. operates solely through authorized provider APIs."
                )

    @staticmethod
    def get_tatkal_advisory() -> str:
        return (
            "Tatkal advisory: F.R.I.D.A.Y. prepares passenger manifests and pre-fills verified credentials, "
            "but strictly connects via authorized IRCTC partner gateways. In DEMO mode, all reservations are simulated "
            "and marked with DEMO-TRAIN-XXXX."
        )


railway_compliance_guard = RailwayComplianceGuard()
