import re

_AADHAAR = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
_PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def redact(text: str) -> str:
    """Mask contact and ID numbers before text leaves our servers. Names and places are kept: matching needs them."""
    text = _AADHAAR.sub("[ID]", text)
    text = _PHONE.sub("[PHONE]", text)
    return _EMAIL.sub("[EMAIL]", text)
