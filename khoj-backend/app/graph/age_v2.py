"""Opt-in age extraction and the number words fixed in the preregistration."""

import re
from typing import Literal
from unicodedata import category, normalize

from pydantic import Field

from app.schemas import Extraction, FieldValue

NUMBER_WORDS = """\
one | एक | ek
two | दो | do
three | तीन | teen, tin
four | चार | chaar, char
five | पाँच, पांच | paanch, panch
six | छह, छः | chhah, chhe, che
seven | सात | saat
eight | आठ | aath
nine | नौ | nau, nao
ten | दस | das, dus
eleven | ग्यारह | gyarah, gyaarah
twelve | बारह | barah, baarah
thirteen | तेरह | terah
fourteen | चौदह | chaudah
fifteen | पंद्रह, पन्द्रह | pandrah
sixteen | सोलह | solah
seventeen | सत्रह | satrah
eighteen | अट्ठारह, अठारह | atharah, attharah
nineteen | उन्नीस | unnees, unnis
twenty | बीस | bees, bis
twenty one | इक्कीस | ikkees, ikkis
twenty two | बाईस | baees, bais
twenty three | तेईस | teis, teees
twenty four | चौबीस | chaubees, chaubis
twenty five | पच्चीस | pachees, pacchis, pachis, pachchis
twenty six | छब्बीस | chhabbees, chhabbis
twenty seven | सत्ताईस | sattais, sattaaees
twenty eight | अट्ठाईस | atthais, athaees
twenty nine | उनतीस | untees, untis
thirty | तीस | tees, tis
thirty one | इकतीस | iktees, iktis
thirty two | बत्तीस | battees, battis
thirty three | तैंतीस | taintees, taintis
thirty four | चौंतीस | chauntees, chauntis
thirty five | पैंतीस | paintees, paintis
thirty six | छत्तीस | chhattees, chhattis
thirty seven | सैंतीस | saintees, saintis
thirty eight | अड़तीस | adtees, adhtis
thirty nine | उनतालीस | untalees, untalis
forty | चालीस | chalees, chalis
forty one | इकतालीस | iktalees, iktalis
forty two | बयालीस | bayalees, bayalis
forty three | तैंतालीस | taintalees, taintalis
forty four | चवालीस, चौवालीस | chavalees, chavalis
forty five | पैंतालीस | paintalees, paintalis
forty six | छियालीस | chhiyalees, chhiyalis
forty seven | सैंतालीस | saintalees, saintalis
forty eight | अड़तालीस | adtalees, adtalis
forty nine | उनचास | unchaas, unchas
fifty | पचास | pachaas, pachas
fifty one | इक्यावन, इक्याबन | ikyavan, ikyawan
fifty two | बावन | bavan, baavan
fifty three | तिरपन | tirpan
fifty four | चौवन | chauvan, chauwan
fifty five | पचपन | pachpan
fifty six | छप्पन | chhappan
fifty seven | सत्तावन | sattavan, sattawan
fifty eight | अट्ठावन | atthavan, atthawan
fifty nine | उनसठ | unsath
sixty | साठ | saathh, saaṭh
sixty one | इकसठ | iksath
sixty two | बासठ | baasath
sixty three | तिरसठ | tirsath
sixty four | चौंसठ | chaunsath
sixty five | पैंसठ | painsath
sixty six | छियासठ | chhiyasath
sixty seven | सड़सठ | sadsath
sixty eight | अड़सठ | adsath
sixty nine | उनहत्तर | unhattar
seventy | सत्तर | sattar
seventy one | इकहत्तर | ikhattar
seventy two | बहत्तर | bahattar
seventy three | तिहत्तर | tihattar
seventy four | चौहत्तर | chauhattar
seventy five | पचहत्तर | pachhattar
seventy six | छिहत्तर | chhihattar
seventy seven | सतहत्तर | sathattar
seventy eight | अठहत्तर, अट्ठहत्तर | athhattar, atthattar
seventy nine | उन्यासी, उनासी | unyasi, unasi
eighty | अस्सी | assi
eighty one | इक्यासी | ikyasi
eighty two | बयासी | bayasi
eighty three | तिरासी | tirasi
eighty four | चौरासी | chaurasi
eighty five | पचासी | pachasi
eighty six | छियासी | chhiyasi
eighty seven | सत्तासी | sattasi
eighty eight | अट्ठासी, अठासी | atthasi, athasi
eighty nine | नवासी | navasi
ninety | नब्बे | nabbe
ninety one | इक्यानवे, इक्यानबे | ikyanve, ikyanave
ninety two | बानवे | baanve, banve
ninety three | तिरानवे | tiranve
ninety four | चौरानवे | chauranve
ninety five | पचानवे | pachanve
ninety six | छियानवे | chhiyanve
ninety seven | सत्तानवे | sattanve
ninety eight | अट्ठानवे, अठानवे | atthanve, athanve
ninety nine | निन्यानवे | ninyanve
one hundred | सौ, एक सौ | sau, ek sau
"""
WORDS = {
    tuple(normalize("NFC", spelling).casefold().split()): number
    for number, row in enumerate(NUMBER_WORDS.splitlines(), 1)
    for column in row.split(" | ")
    for spelling in column.split(", ")
}
MAX_WORDS = max(map(len, WORDS))
AGE_INSTRUCTIONS = (
    "Use age_min, age_max and age_evidence for age instead of an age entry in fields. "
    "For a single age use the same integer in both bounds. For a range use its ordered "
    "inclusive bounds. Copy the exact source quote into age_evidence. For unknown age "
    "leave all three null. These age instructions supersede the age examples above. "
    "For names, use the source spelling and script for both the value and its quote."
)


class ExtractionV2(Extraction):
    age_min: int | None = Field(default=None, strict=True, description="Inclusive lower age")
    age_max: int | None = Field(default=None, strict=True, description="Inclusive upper age")
    age_evidence: str | None = Field(
        default=None, description="Exact quote from the current message"
    )


def numbers_in(quote: str) -> set[int]:
    # Keep combining marks attached to their letters, including Devanagari matras.
    text = normalize("NFC", quote).casefold()
    tokens = re.split(
        r"\s+|[-‐‑–—]",
        "".join(
            c if category(c)[0] in "LMN" or c.isspace() or c in "-‐‑–—" else "\x00" for c in text
        ),
    )
    found: set[int] = set()
    for segment in " ".join(tokens).split("\x00"):
        words = segment.split()
        index = 0
        while index < len(words):
            for size in range(min(MAX_WORDS, len(words) - index), 0, -1):
                phrase = tuple(words[index : index + size])
                if phrase in WORDS:
                    found.add(WORDS[phrase])
                    index += size
                    break
            else:
                word = words[index]
                if word.isdecimal():
                    try:
                        found.add(int(word))
                    except ValueError:
                        # Python bounds conversion of unreasonably long integers.
                        pass
                index += 1
    return found


AgeDrop = Literal["quote_missing", "number_missing"]


def ground_age(text: str, extraction: ExtractionV2) -> tuple[FieldValue | None, AgeDrop | None]:
    low, high, evidence = extraction.age_min, extraction.age_max, extraction.age_evidence
    if low is None and high is None and evidence is None:
        return None, None
    if not evidence or normalize("NFC", evidence) not in normalize("NFC", text):
        return None, "quote_missing"
    numbers = numbers_in(evidence)
    if low is None or high is None or low < 0 or not 0 < high - low + 1 <= len(numbers):
        return None, "number_missing"
    if any(n not in numbers for n in range(low, high + 1)):
        return None, "number_missing"
    value = str(low) if low == high else f"{low}-{high}"
    return FieldValue(name="age", value=value, evidence=evidence), None
