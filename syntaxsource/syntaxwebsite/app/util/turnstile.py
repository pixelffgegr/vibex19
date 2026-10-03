# Captcha has been removed from VibeX19 entirely.
# VerifyToken is kept as a no-op so existing call sites keep working.
#
# IsEnabled() exists because "no captcha" has to mean the whole feature is off,
# not just that verification passes. With CloudflareTurnstileSiteKey empty the
# Turnstile widget cannot initialise, so it never writes a hidden
# cf-turnstile-response input - any view that requires that field then rejects
# every single submission (giftcard redeem, messages, email change, audio
# migrator all reported "Please fill in all the fields" / "Please complete the
# captcha"). Views and templates must gate on IsEnabled() instead.

from config import Config


def IsEnabled() -> bool:
    """
        Whether a captcha is actually configured for this deployment.

        :returns: True only when a Cloudflare Turnstile site key is set.
    """
    return bool(Config.CloudflareTurnstileSiteKey)


def VerifyToken(token: str) -> bool:
    """
        Captcha verification stub - VibeX19 ships without captcha.

        :param token: Ignored
        :returns: Always True
    """
    return True