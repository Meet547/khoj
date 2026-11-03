# Age v3 preregistration

2026-11-03 (Asia/Kolkata)

Reviewer status: pending

## Cases and execution

Run v1 and v2 on all 60 frozen cases. Use text input through the production
intake path, with a fresh durable-intake turn and an empty draft per case and
schema. Use production model routing. Map Hinglish to the production Hindi
locale for routing and retain Hinglish as a scoring stratum. There is no repeat
set.

The runner enforces hard caps of 120 extractions and 170 Ollama chat attempts.
It reserves an extraction before calling the production extraction router and
reserves an attempt before each provider call, including retries, repairs and
fallbacks. It stops if either cap would be exceeded. Log model, phase, retry,
outcome and timing for each chat attempt.

## Schema and grounding

The v2 extraction schema adds `age_min` and `age_max` as nullable integers and `age_evidence` as a nullable string. For a known single age, both bounds equal that age. For a range, both bounds are required and ordered. A missing age uses nulls. In v2, the structured age is the sole model output used for age.

Keep a proposed age only if the nonempty evidence is an exact substring of the current case text after NFC normalisation. Otherwise drop it with `quote_missing`. Then require both bounds and require every integer in the inclusive range to appear explicitly in that quote after number-word mapping. Otherwise drop it with `number_missing`. Endpoints alone do not establish intermediate ages. Record one reason per drop, with the quote check first. Decimal-digit tokens (including Devanagari) are read as integers. Match number words after NFC and case folding. Match the longest phrase first, allowing spaces or a hyphen between its words. The table below fixes accepted word spellings. A wholly absent age does not count as a grounding drop.

## Scoring

A v1 scalar age `n` counts as `[n, n]`. A range is correct if it overlaps the labelled range, with no tolerance. Recall divides correct ages by non-null age labels. Precision divides correct ages by emitted age values, including values on null labels and malformed v1 age values. Report numerators and denominators overall and by corpus language. A zero denominator is reported as unavailable.

Score name, relation, gender, last_seen_place, last_seen_time, height_build, marks, clothing, language_spoken and health_or_special_needs by exact match after NFC and case folding. Names keep their source spelling. Use no alias list. For scoring, use the production draft's `language` for `language_spoken`, `conditions` for `health_or_special_needs`, and either `height` or `build` for `height_build`. When both height and build are emitted, each must match the single expected value. Report exact accuracy on all 60 cases and recall on non-null labels, with denominators. Compare non-null recall for the promotion threshold.

A null label is correct only when the draft contains no value for the field. Any emitted value for a null label is wrong. A mismatched value for a non-null label is also wrong. Gender must have zero wrong values. An absent extraction for a non-null label reduces recall. A model-unavailable turn is scored as missing and identified in the report.

## Promotion

V2 becomes the default only if all four conditions hold.

1. V2 age recall is at least 75% on the 42 non-null age labels.
2. No non-age field's non-null recall falls more than five percentage points below v1.
3. V2 gender has zero wrong values.
4. The manifest contains a line beginning `Reviewer status: signed off by`.

If condition 4 is unmet, record `promotion_blocked: unreviewed labels` and
begin the report with the following line.

Owner-labelled, unreviewed held-out labels. Promotion blocked pending reviewer sign-off.

With 42 age labels, the 95% interval on recall is roughly ±15 percentage
points, so a result near 75% is not decisive.

## Fixed number-word table

Hindi spelling reference: [National Institute of Technology Hamirpur Hindi counting chart](https://nith.ac.in/library/hindi/hindi_count.php). Roman spellings are fixed evaluation variants.

| Digits | English | Hindi | Hinglish |
| --- | --- | --- | --- |
| 1 | one | एक | ek |
| 2 | two | दो | do |
| 3 | three | तीन | teen, tin |
| 4 | four | चार | chaar, char |
| 5 | five | पाँच, पांच | paanch, panch |
| 6 | six | छह, छः | chhah, chhe, che |
| 7 | seven | सात | saat |
| 8 | eight | आठ | aath |
| 9 | nine | नौ | nau, nao |
| 10 | ten | दस | das, dus |
| 11 | eleven | ग्यारह | gyarah, gyaarah |
| 12 | twelve | बारह | barah, baarah |
| 13 | thirteen | तेरह | terah |
| 14 | fourteen | चौदह | chaudah |
| 15 | fifteen | पंद्रह, पन्द्रह | pandrah |
| 16 | sixteen | सोलह | solah |
| 17 | seventeen | सत्रह | satrah |
| 18 | eighteen | अट्ठारह, अठारह | atharah, attharah |
| 19 | nineteen | उन्नीस | unnees, unnis |
| 20 | twenty | बीस | bees, bis |
| 21 | twenty one | इक्कीस | ikkees, ikkis |
| 22 | twenty two | बाईस | baees, bais |
| 23 | twenty three | तेईस | teis, teees |
| 24 | twenty four | चौबीस | chaubees, chaubis |
| 25 | twenty five | पच्चीस | pachees, pacchis, pachis, pachchis |
| 26 | twenty six | छब्बीस | chhabbees, chhabbis |
| 27 | twenty seven | सत्ताईस | sattais, sattaaees |
| 28 | twenty eight | अट्ठाईस | atthais, athaees |
| 29 | twenty nine | उनतीस | untees, untis |
| 30 | thirty | तीस | tees, tis |
| 31 | thirty one | इकतीस | iktees, iktis |
| 32 | thirty two | बत्तीस | battees, battis |
| 33 | thirty three | तैंतीस | taintees, taintis |
| 34 | thirty four | चौंतीस | chauntees, chauntis |
| 35 | thirty five | पैंतीस | paintees, paintis |
| 36 | thirty six | छत्तीस | chhattees, chhattis |
| 37 | thirty seven | सैंतीस | saintees, saintis |
| 38 | thirty eight | अड़तीस | adtees, adhtis |
| 39 | thirty nine | उनतालीस | untalees, untalis |
| 40 | forty | चालीस | chalees, chalis |
| 41 | forty one | इकतालीस | iktalees, iktalis |
| 42 | forty two | बयालीस | bayalees, bayalis |
| 43 | forty three | तैंतालीस | taintalees, taintalis |
| 44 | forty four | चवालीस, चौवालीस | chavalees, chavalis |
| 45 | forty five | पैंतालीस | paintalees, paintalis |
| 46 | forty six | छियालीस | chhiyalees, chhiyalis |
| 47 | forty seven | सैंतालीस | saintalees, saintalis |
| 48 | forty eight | अड़तालीस | adtalees, adtalis |
| 49 | forty nine | उनचास | unchaas, unchas |
| 50 | fifty | पचास | pachaas, pachas |
| 51 | fifty one | इक्यावन, इक्याबन | ikyavan, ikyawan |
| 52 | fifty two | बावन | bavan, baavan |
| 53 | fifty three | तिरपन | tirpan |
| 54 | fifty four | चौवन | chauvan, chauwan |
| 55 | fifty five | पचपन | pachpan |
| 56 | fifty six | छप्पन | chhappan |
| 57 | fifty seven | सत्तावन | sattavan, sattawan |
| 58 | fifty eight | अट्ठावन | atthavan, atthawan |
| 59 | fifty nine | उनसठ | unsath |
| 60 | sixty | साठ | saathh, saaṭh |
| 61 | sixty one | इकसठ | iksath |
| 62 | sixty two | बासठ | baasath |
| 63 | sixty three | तिरसठ | tirsath |
| 64 | sixty four | चौंसठ | chaunsath |
| 65 | sixty five | पैंसठ | painsath |
| 66 | sixty six | छियासठ | chhiyasath |
| 67 | sixty seven | सड़सठ | sadsath |
| 68 | sixty eight | अड़सठ | adsath |
| 69 | sixty nine | उनहत्तर | unhattar |
| 70 | seventy | सत्तर | sattar |
| 71 | seventy one | इकहत्तर | ikhattar |
| 72 | seventy two | बहत्तर | bahattar |
| 73 | seventy three | तिहत्तर | tihattar |
| 74 | seventy four | चौहत्तर | chauhattar |
| 75 | seventy five | पचहत्तर | pachhattar |
| 76 | seventy six | छिहत्तर | chhihattar |
| 77 | seventy seven | सतहत्तर | sathattar |
| 78 | seventy eight | अठहत्तर, अट्ठहत्तर | athhattar, atthattar |
| 79 | seventy nine | उन्यासी, उनासी | unyasi, unasi |
| 80 | eighty | अस्सी | assi |
| 81 | eighty one | इक्यासी | ikyasi |
| 82 | eighty two | बयासी | bayasi |
| 83 | eighty three | तिरासी | tirasi |
| 84 | eighty four | चौरासी | chaurasi |
| 85 | eighty five | पचासी | pachasi |
| 86 | eighty six | छियासी | chhiyasi |
| 87 | eighty seven | सत्तासी | sattasi |
| 88 | eighty eight | अट्ठासी, अठासी | atthasi, athasi |
| 89 | eighty nine | नवासी | navasi |
| 90 | ninety | नब्बे | nabbe |
| 91 | ninety one | इक्यानवे, इक्यानबे | ikyanve, ikyanave |
| 92 | ninety two | बानवे | baanve, banve |
| 93 | ninety three | तिरानवे | tiranve |
| 94 | ninety four | चौरानवे | chauranve |
| 95 | ninety five | पचानवे | pachanve |
| 96 | ninety six | छियानवे | chhiyanve |
| 97 | ninety seven | सत्तानवे | sattanve |
| 98 | ninety eight | अट्ठानवे, अठानवे | atthanve, athanve |
| 99 | ninety nine | निन्यानवे | ninyanve |
| 100 | one hundred | सौ, एक सौ | sau, ek sau |
