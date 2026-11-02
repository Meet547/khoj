"""Deterministic safety shortcuts execute before any model call."""

import re

EMERGENCY = re.compile(
    r"\b(emergency|immediate danger|bleeding|kidnapp\w*|abduct\w*|in danger|bachao|khatra|khatre|apaatkal)\b|"
    r"बचाओ|खतरे में|ख़तरे में|आपात|अपहरण|खून बह|धोका|वाचवा|জরুরি|বাঁচাও|অপহরণ|"
    r"அவசரம்|காப்பாற்று|కాపాడండి|అత్యవసర|ಅಪಾಯ|ಕಾಪಾಡಿ|അപകടം|രക്ഷിക്കൂ|કટોકટી|બચાવો|ਐਮਰਜੈਂਸੀ|ਬਚਾਓ",
    re.I,
)
CANCEL = re.compile(
    r"^\s*((?:please\s+)?(?:cancel|stop|quit)(?:\s+(?:this|the|my|intake|report|conversation|session))*|"
    r"(?:कृपया\s+)?(?:रद्द|रद्द करो|बंद करो|रोक दो)|रद्द करा|থামুন|বাতিল|நிறுத்து|రద్దు|ರದ್ದು|റദ്ദാക്കുക|રદ|ਰੱਦ)[.!।\s]*$",
    re.I,
)
HELP = re.compile(
    r"^\s*(help|help me|i need help|please help(?: me)?|मदद|मदद करें|मुझे मदद चाहिए|कृपया मदद करें|सहायता|मदत|मदत करा|সাহায্য|உதவி|సహాయం|ಸಹಾಯ|സഹായം|મદદ|ਮਦਦ)[.!।\s]*$",
    re.I,
)
SKIP = re.compile(
    r"^\s*(skip|(?:i )?don't know|(?:i )?do not know|unknown|pata nahi|nahi pata|नहीं मालूम|पता नहीं|नहीं पता|छोड़ो|माहित नाही)[.!।\s]*$",
    re.I,
)


def triage(text: str) -> str | None:
    if EMERGENCY.search(text):
        return "emergency"
    if CANCEL.fullmatch(text):
        return "cancel"
    if HELP.fullmatch(text):
        return "help"
    return None
