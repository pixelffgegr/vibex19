# Captcha has been removed from VibeX19 entirely.
# VerifyToken is kept as a no-op so existing call sites keep working.


def VerifyToken(token: str) -> bool:
    """
        Captcha verification stub - VibeX19 ships without captcha.

        :param token: Ignored
        :returns: Always True
    """
    return True
