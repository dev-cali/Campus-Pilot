"""Temporary deterministic keyword retrieval, not embeddings or Pinecone."""

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Callable, Protocol

from ai.document_processing import DocumentChunk


MAX_QUESTION_CHARS = 2000
MAX_EVIDENCE_CHUNKS = 2
MAX_EVIDENCE_CHARS = 2000
STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "had", "has", "have",
    "how", "i", "if", "in", "into", "is", "it", "me", "my", "of", "on", "or", "please",
    "should", "s", "tell", "that", "the", "these", "this", "to", "was", "were", "what",
    "when", "where", "which", "who", "with", "would", "you", "your", "fictional",
    "demo", "campus", "university",
})

LOW_INFORMATION_WEIGHTS = {
    "available": 0.12, "current": 0.12, "simulated": 0.2, "catalog": 0.15,
    "first": 0.12, "next": 0.12, "day": 0.2, "term": 0.25,
}
TITLE_WEIGHT = 0.22
EXPANSION_WEIGHT = 0.42
MIN_RELEVANCE_SCORE = 1.35

_TOKEN_EQUIVALENTS = {
    "scholarships": "scholarship", "installments": "installment", "courses": "course",
    "subjects": "subject", "grades": "grade", "grading": "grade", "classes": "class",
    "programs": "program", "awards": "award", "requirements": "requirement",
    "prerequisites": "prerequisite", "learners": "learner", "students": "student",
    "applications": "application", "offices": "office", "units": "unit", "days": "day", "fees": "fee",
    "charges": "charge", "credit": "unit", "credits": "unit",
    "costs": "cost", "payments": "payment", "opens": "open", "opening": "open", "begins": "begin",
    "started": "start", "starts": "start", "enroll": "enrollment", "enrolling": "enrollment",
    "closes": "close", "closed": "close", "closing": "close",
    "register": "registration", "registered": "registration", "passing": "pass",
    "passed": "pass", "passes": "pass", "requires": "require", "required": "require",
    "requiring": "require", "appeals": "appeal", "withdrawal": "withdraw",
    "withdrawals": "withdraw", "transcripts": "transcript", "records": "record",
    "advisers": "adviser", "advisors": "adviser", "checks": "check", "confirms": "confirm",
    "confirmation": "confirm", "verifies": "verify", "verified": "verify",
    "counts": "count", "items": "item", "needed": "need", "applies": "application",
    "applying": "application", "applied": "application",
    "amounts": "amount", "qualifies": "qualify", "qualifying": "qualify",
    "apply": "application",
    "incoming": "new",
    "explains": "explain", "explained": "explain",
}

# Small, bidirectional domain paraphrases. Original terms retain full weight;
# these supplementary signals cannot outweigh a direct content match.
_PHRASE_EXPANSIONS = (
    (("sign", "up"), ("enrollment",)),
    (("register",), ("enrollment",)),
    (("school", "bill"), ("tuition", "fee")),
    (("school", "charges"), ("tuition", "fee")),
    (("split", "payment"), ("installment", "plan")),
    (("split", "school", "bill"), ("installment", "payment", "tuition", "plan")),
    (("spread", "charges"), ("installment", "payment")),
    (("spread", "payment"), ("installment", "payment", "plan")),
    (("fee",), ("charge", "cost")),
    (("prerequisite",), ("require", "pass")),
    (("passing", "mark"), ("pass", "grade")),
    (("mark", "count", "pass"), ("grade", "pass")),
    (("financial", "assistance"), ("scholarship", "grant")),
    (("academic", "records"), ("transcript",)),
    (("subject", "grade"), ("transcript",)),
    (("ask", "list"), ("transcript", "request")),
    (("change", "subject"), ("add", "drop", "course")),
    (("change", "course"), ("add", "drop", "calendar")),
    (("course", "requirement"), ("prerequisite", "require")),
    (("school", "start"), ("class", "begin")),
    (("class", "back"), ("class", "begin")),
    (("course", "load"), ("unit",)),
    (("installment", "amount"), ("payment", "balance")),
    (("first", "sign", "up"), ("enrollment", "registration")),
    (("get", "scholarship"), ("eligibility", "award")),
    (("gpa", "limit"), ("threshold",)),
    (("cutoff",), ("threshold", "require")),
    (("guarantee", "award"), ("actual", "award", "entitlement")),
    (("who", "check"), ("adviser", "verify")),
    (("who", "confirm"), ("adviser", "verify")),
    (("estimate", "total"), ("tuition", "fee")),
    (("until", "enrollment"), ("close", "deadline")),
    (("application", "item"), ("form", "summary")),
)

_PERSONAL_RECORD_RE = re.compile(
    r"\bmy\b.{0,60}\b(?:gpa|grades?|balance|enrollment\s+status|academic\s+records?)\b"
    r"|\b(?:another|other)\s+(?:learner|student)(?:'s)?\b.{0,40}\b(?:gpa|grades?|records?)\b"
    r"|\boutstanding\s+(?:tuition\s+)?balance\b",
)
_PROCEDURAL_RECORD_RE = re.compile(
    r"\b(?:how|where)\b.{0,80}\b(?:request|ask|get|receive)\b.{0,70}"
    r"\b(?:transcript|record|certificate|list|copy)\b"
)
_QUESTION_STARTERS = frozenset({
    "what", "when", "where", "which", "who", "how", "can", "does", "do",
    "is", "are", "would", "could", "should", "for", "tell", "show", "ignore", "print", "if", "explain",
    "describe", "list", "summarize", "on", "until", "estimate",
})
_GENERIC_CAPITALIZED_TERMS = frozenset({
    "university", "school", "term", "january", "february", "march", "april",
    "may", "june", "july", "august", "september", "october", "november",
    "december", "gpa", "php",
})


class PublicChunkSource(Protocol):
    """Storage interface: return only currently eligible public passages."""

    def public_chunks(self, *, reference_date: date) -> tuple[DocumentChunk, ...]:
        ...


@dataclass(frozen=True)
class Evidence:
    """Request-local citation ID plus trusted source data; score is not truth."""

    evidence_id: str
    chunk: DocumentChunk
    matched_terms: tuple[str, ...]


def validate_evidence_budget(evidence: tuple[Evidence, ...]) -> None:
    """Reject unusable/oversized evidence; never cut passages or drop context.

    Eligibility remains the source's responsibility. These are additional
    preflight checks, not proof that the evidence answers the question.
    """
    if not 1 <= len(evidence) <= MAX_EVIDENCE_CHUNKS:
        raise ValueError("invalid_evidence_budget")
    if len({item.evidence_id for item in evidence}) != len(evidence):
        raise ValueError("invalid_evidence")
    if any(not item.evidence_id.strip() or len(item.evidence_id) > 20
           or not item.chunk.chunk_text.strip() or not item.chunk.version
           for item in evidence):
        raise ValueError("invalid_evidence")
    if sum(len(item.chunk.chunk_text) for item in evidence) > MAX_EVIDENCE_CHARS:
        raise ValueError("evidence_budget_exceeded")


class Retriever(Protocol):
    """Future Pinecone adapter can return this same evidence contract.

    Every implementation must apply authoritative eligibility checks before
    returning content. The type declaration alone cannot enforce that rule.
    """

    def retrieve(self, question: str, *, reference_date: date) -> tuple[Evidence, ...]:
        ...


def validate_question(question: object) -> str:
    """Reject bad input with a fixed code; never silently truncate a question."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("invalid_question")
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError("question_too_long")
    return question.strip()


def _canonical_token(token: str) -> str:
    return _TOKEN_EQUIVALENTS.get(token, token)


def _tokens(text: str, *, remove_stop_words: bool = True) -> tuple[str, ...]:
    """Normalize Unicode, punctuation, common number formats, and safe inflections."""
    value = unicodedata.normalize("NFKC", text).casefold()
    value = re.sub(
        r"₱\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
        lambda match: " php " + match.group(1).replace(",", ""), value,
    )
    value = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", value)
    value = value.replace("&", " and ")
    value = re.sub(r"[/\\‐‑‒–—-]+", " ", value)
    result = []
    for raw in re.findall(r"[^\W_]+(?:\.[0-9]+)?", value, flags=re.UNICODE):
        token = _canonical_token(raw)
        if not remove_stop_words or token not in STOP_WORDS:
            result.append(token)
    return tuple(result)


def _terms(text: str) -> set[str]:
    """Content terms used for corpus statistics and passage matching."""
    return set(_tokens(text))


def _passage_tokens(text: str) -> tuple[str, ...]:
    """Remove the repeated fiction label so it cannot act as retrieval evidence."""
    body = re.sub(r"^\s*FICTIONAL\s+TEST\s+DATA\s*\.\s*", "", text,
                  count=1, flags=re.IGNORECASE)
    return _tokens(body)


def _contains_sequence(tokens: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    if not phrase or len(phrase) > len(tokens):
        return False
    return any(tokens[index:index + len(phrase)] == phrase
               for index in range(len(tokens) - len(phrase) + 1))


def _contains_ordered_terms(tokens: tuple[str, ...], phrase: tuple[str, ...],
                            max_gap: int = 2) -> bool:
    """Match short concept phrases despite intervening modifiers or auxiliaries."""
    if not phrase or not tokens:
        return False
    positions = [index for index, token in enumerate(tokens) if token == phrase[0]]
    for start in positions:
        cursor = start
        for term in phrase[1:]:
            try:
                cursor = next(index for index in range(cursor + 1,
                                                       min(len(tokens), cursor + max_gap + 2))
                              if tokens[index] == term)
            except StopIteration:
                break
        else:
            return True
    return False


def _is_personal_record_request(question: str) -> bool:
    """Avoid treating public policy passages as evidence of a person's record."""
    normalized = unicodedata.normalize("NFKC", question).casefold()
    if re.search(
        r"\b(?:another|other)\s+(?:learner|student)(?:'s)?\b.{0,40}"
        r"\b(?:gpa|grades?|records?)\b", normalized,
    ):
        return True
    return bool(_PERSONAL_RECORD_RE.search(normalized)
                and not _PROCEDURAL_RECORD_RE.search(normalized))


def _named_terms(question: str) -> frozenset[str]:
    """Retain proper-name signals such as Data Fundamentals and Lakbay."""
    words = re.findall(r"[^\W_]+(?:\.[0-9]+)?", unicodedata.normalize("NFKC", question),
                       flags=re.UNICODE)
    named = set()
    for index, word in enumerate(words):
        normalized = _canonical_token(word.casefold())
        if index == 0 and normalized in _QUESTION_STARTERS:
            continue
        if len(word) < 2 or not word[0].isupper() or normalized in _GENERIC_CAPITALIZED_TERMS:
            continue
        if normalized.isdigit() or re.fullmatch(r"\d+(?:\.\d+)?", normalized):
            continue
        named.add(normalized)
    return frozenset(named)


def _query_profile(question: str) -> tuple[
    dict[str, float], frozenset[str], tuple[tuple[str, ...], ...], frozenset[str], frozenset[str]
]:
    all_tokens = _tokens(question, remove_stop_words=False)
    tokens = tuple(token for token in all_tokens if token not in STOP_WORDS)
    role_question = bool(
        re.search(r"\bwho\b", question, re.IGNORECASE)
        and re.search(r"\b(?:check|verify|confirm)\w*\b", question, re.IGNORECASE)
    )
    weights: dict[str, float] = {}
    for token in tokens:
        weights[token] = max(weights.get(token, 0.0), LOW_INFORMATION_WEIGHTS.get(token, 1.0))
    original = frozenset(weights)
    expansion_terms: set[str] = set()
    alias_phrases: list[tuple[str, ...]] = []
    for source, target_terms in _PHRASE_EXPANSIONS:
        if source == ("prerequisite",) and role_question:
            continue
        source_tokens = tuple(_canonical_token(token) for token in source)
        # Phrase matching ignores grammatical stop words, while personal-intent
        # detection above always sees the original wording.
        filtered_source = tuple(token for token in source_tokens if token not in STOP_WORDS)
        if filtered_source and (
            _contains_sequence(tokens, filtered_source)
            or _contains_ordered_terms(
                tokens, filtered_source,
                max_gap=4 if filtered_source in {("spread", "payment"),
                                                  ("spread", "charge")} else 2,
            )
        ):
            mapped = tuple(_canonical_token(term) for term in target_terms)
            expansion_terms.update(mapped)
            alias_phrases.append(mapped)
            for target in mapped:
                weights[target] = max(weights.get(target, 0.0), EXPANSION_WEIGHT)

    phrases = tuple(dict.fromkeys((*(
        (tokens[index], tokens[index + 1])
        for index in range(len(tokens) - 1)
        if tokens[index] != tokens[index + 1]
    ), *alias_phrases)))
    return weights, original, phrases, frozenset(expansion_terms), _named_terms(question)


def _split_question_clauses(question: str) -> tuple[str, ...]:
    """Lightweight two-part segmentation; it is a ranking hint, not a parser."""
    parts = re.split(
        r",\s*(?=(?:and\s+)?(?:when|what|who|where|how|which|whether|can|does|do|is)\b)"
        r"|;\s*|\band\s+(?=(?:when|what|who|where|how|which|whether|can|does|do|is)\b)",
        question, maxsplit=1, flags=re.IGNORECASE,
    )
    parts = tuple(part.strip(" ,;?") for part in parts if part.strip(" ,;?"))
    if len(parts) == 2 and all(_tokens(part) for part in parts):
        return parts
    return (question,)


def _inverse_document_frequency(term: str, document_frequency: Counter, corpus_size: int) -> float:
    frequency = document_frequency.get(term, 0)
    # IDF = 1 + ln(1 + (N - df + 0.5) / (df + 0.5)). The unit floor keeps a
    # single distinctive term retrievable in the small legacy corpus.
    return 1.0 + math.log(1.0 + (corpus_size - frequency + 0.5) / (frequency + 0.5))


def _prepare_profile(profile, document_frequency: Counter, corpus_size: int):
    weights, original_terms, phrases, expansion_terms, named_terms = profile
    weighted_terms = tuple(
        (term, weight, _inverse_document_frequency(term, document_frequency, corpus_size))
        for term, weight in sorted(weights.items())
    )
    denominator = sum(idf * weight for term, weight, idf in weighted_terms
                      if term in original_terms)
    return (weighted_terms, original_terms, phrases, expansion_terms, named_terms, denominator)


def _score_profile(
    profile,
    body_tokens: tuple[str, ...], title_tokens: tuple[str, ...],
    body: set[str] | None = None, title: set[str] | None = None,
) -> tuple[float, frozenset[str], frozenset[str], float, float, float]:
    """IDF-weight distinct body terms; title hits weigh 0.22, phrases add fixed bonuses."""
    weighted_terms, original_terms, phrases, expansion_terms, named_terms, denominator = profile
    body = body if body is not None else set(body_tokens)
    title = title if title is not None else set(title_tokens)
    score = 0.0
    body_matches: set[str] = set()
    title_matches: set[str] = set()
    covered_weight = 0.0
    for term, weight, idf in weighted_terms:
        if term in body:
            score += idf * weight
            if term in original_terms:
                body_matches.add(term)
                covered_weight += idf * weight
        elif term in title:
            score += idf * weight * TITLE_WEIGHT
            if term in original_terms:
                title_matches.add(term)
                covered_weight += idf * weight * TITLE_WEIGHT

    phrase_bonus = 0.0
    for phrase in phrases:
        if len(phrase) == 1 and phrase[0] in body:
            phrase_bonus += 1.5
            continue
        if _contains_sequence(body_tokens, phrase):
            phrase_bonus += 1.5
            continue
        if all(term in body for term in phrase):
            positions = [index for index, token in enumerate(body_tokens) if token in phrase]
            if positions and max(positions) - min(positions) <= 10:
                phrase_bonus += 0.9
    phrase_bonus = min(3.0, phrase_bonus)
    score += phrase_bonus
    coverage = covered_weight / denominator if denominator else 0.0
    named_coverage = (len(named_terms & body) / len(named_terms) if named_terms else 1.0)
    if named_terms and named_coverage == 1.0:
        score += 3.0
    return (score, frozenset(body_matches), frozenset(title_matches), coverage,
            phrase_bonus, named_coverage)


def _candidate_is_relevant(score: float, body_matches: frozenset[str], coverage: float,
                            phrase_bonus: float, expansion_matches: int,
                            named_coverage: float, named_terms: frozenset[str],
                            original_terms: frozenset[str]) -> bool:
    substantive_terms = original_terms - named_terms
    substantive_matches = body_matches - named_terms
    has_substantive_signal = (
        not substantive_terms or bool(substantive_matches) or expansion_matches >= 2
        or (named_coverage == 1.0 and expansion_matches >= 1)
    )
    return score >= MIN_RELEVANCE_SCORE and (
        len(body_matches) >= 2 or coverage >= 0.65 or phrase_bonus >= 1.0
        or expansion_matches >= 1
    ) and has_substantive_signal and (named_coverage == 1.0 or expansion_matches >= 2)


def _program_list_bonus(question: str, passage: str) -> float:
    """Prefer an enumerated catalog overview for program-list requests."""
    question_tokens = set(_tokens(question, remove_stop_words=False))
    if not question_tokens & {"degree", "program"}:
        return 0.0
    if not question_tokens & {"which", "what", "all", "available"}:
        return 0.0
    markers = re.findall(
        r"(?<![A-Za-z0-9])(?:B\.S\.|B\.A\.|BS|BA|BSc|MS|MA|PhD)(?![A-Za-z0-9])",
        passage,
        flags=re.IGNORECASE,
    )
    return 2.5 * max(0, len(markers) - 1)


def _numeric_answer_bonus(question: str, passage: str) -> float:
    """Prefer actual amounts when the question asks for a monetary quantity."""
    q = unicodedata.normalize("NFKC", question).casefold()
    has_currency_or_percent = bool(re.search(r"₱\s*\d|\bphp\s*\d|\d+(?:\.\d+)?\s*%", passage, re.I))
    if not has_currency_or_percent:
        return 0.0
    asks_return_amount = bool(
        re.search(r"\brefund\w*\b", q)
        or (re.search(r"\b(?:come|comes|coming)\s+back\b|\bmoney\s+back\b|\breimburse\w*\b", q)
            and re.search(r"\bwithdraw\w*\b", q))
    )
    if re.search(r"\bhow\s+much\b", q) and asks_return_amount:
        if re.search(
            r"refund\w*.{0,20}(?:\d+(?:\.\d+)?\s*%|₱|\bphp\s*\d)"
            r"|(?:\d+(?:\.\d+)?\s*%|₱|\bphp\s*\d).{0,20}refund\w*",
            passage, flags=re.IGNORECASE | re.DOTALL,
        ):
            return 3.0
        return 0.0
    if re.search(r"\bhow\s+much\b|\b(?:amount|price|fee)\b", q):
        return 1.0
    return 0.0


def _dated_event_bonus(question: str, passage: str, body_terms: set[str] | None = None) -> float:
    """Use a date only when the passage also matches the event being asked about."""
    q_terms = set(_tokens(question))
    body_terms = body_terms if body_terms is not None else set(_passage_tokens(passage))
    if (not q_terms & {"deadline", "due", "date", "start", "begin", "open"}
            and not re.search(r"\bwhen\b|\buntil\b", question, re.IGNORECASE)):
        return 0.0
    event_terms = {
        "enrollment", "registration", "withdraw", "installment", "payment",
        "class", "orientation", "scholarship", "add", "drop",
    }
    requested_events = q_terms & event_terms
    if not requested_events or not body_terms & requested_events:
        return 0.0
    if not re.search(
        r"\b(?:january|february|march|april|may|june|july|august|september|"
        r"october|november|december)\s+\d{1,2}\b",
        passage, flags=re.IGNORECASE,
    ):
        return 0.0
    return 1.5


def _nearby_event_values(question: str, passage: str, anchor_question: str) -> dict[str, bool]:
    """Check whether dates, clock times, and venues are tied to the asked event."""
    excluded = {
        "when", "where", "what", "time", "date", "start", "begin", "open",
        "held", "venue", "location", "window", "deadline", "due", "help",
        "get", "find", "provided", "shuttle", "event", "session", "term",
    }
    anchors = {term for term in _tokens(anchor_question)
               if len(term) >= 4 and term not in excluded}
    if not anchors:
        return {"date": False, "time": False, "venue": False}
    passage_folded = passage.casefold()
    anchor_positions = [
        match.start() for term in anchors
        for match in re.finditer(rf"\b{re.escape(term)}\b", passage_folded)
    ]

    def near(pattern):
        return any(
            abs(value.start() - anchor) <= 120
            for value in re.finditer(pattern, passage, flags=re.IGNORECASE)
            for anchor in anchor_positions
        )

    return {
        "date": near(r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b"),
        "time": near(r"\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?|noon)\b"),
        "venue": near(r"\b(?:at|in)\s+(?:the\s+)?[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,3}"),
    }


def _event_attribute_bonus(question: str, passage: str,
                           anchor_question: str | None = None) -> float:
    """Reward requested event fields only when they occur near the event name."""
    values = _nearby_event_values(question, passage, anchor_question or question)
    score = 0.0
    if re.search(r"\b(?:what\s+time|time)\b", question, re.IGNORECASE) and values["time"]:
        score += 2.0
    if re.search(r"\b(?:where|venue|location|held)\b", question, re.IGNORECASE) and values["venue"]:
        score += 2.0
    if (re.search(r"\bwhen\b", question, re.IGNORECASE) and values["date"]
            and re.search(r"\b(?:orientation|session|meeting|event)\b", anchor_question or question,
                          re.IGNORECASE)
            and values["time"] and values["venue"]):
        score += 0.75
    return score


def _answer_type_bonus(question: str, passage: str) -> float:
    """Prefer evidence that expresses the requested kind of financial fact."""
    q = unicodedata.normalize("NFKC", question).casefold()
    bonus = 0.0
    requests_itemized_fixed_charges = bool(
        re.search(r"\b(?:what|which)\b", q)
        and re.search(r"\b(?:fixed\b.*\b(?:fees?|charges?|costs?)\b|"
                      r"(?:categories|items|breakdown)\b.*\bfixed\b|"
                      r"fees?\b.*\badded\b.*\btuition\b)", q)
        and re.search(r"\b(?:add|added|include|included|breakdown|categories|items|make\s+up|consist|are)\b", q)
    )
    if (requests_itemized_fixed_charges
            and re.search(r"\b(?:fees?|charges?|costs?)\b", q)
            and re.search(r"fixed\s+(?:charges|fees)\s*:", passage, re.I)
            and len(re.findall(r"₱\s*\d", passage)) >= 3):
        bonus += 5.0
    if (re.search(r"\b(?:cost|total|estimate|estimated)\b", q)
            and re.search(r"\bunits?\b", q)
            and re.search(r"\bper\s+unit\b", passage, re.I)
            and re.search(r"fixed\s+charges\s*:", passage, re.I)):
        bonus += 3.0
    if _requests_unit_rate(question) and _provides_unit_rate(passage):
        bonus += 5.0
    if (re.search(r"\b(?:spread|split)\b", q)
            and re.search(r"\b(?:installments?|payments?)\b", q)
            and re.search(r"\b(?:optional|payment)\s+(?:simulated\s+)?plan\b", passage, re.I)):
        bonus += 2.0
    if (re.search(r"\binstallment\w*\b", q)
            and re.search(r"\b(?:plan|extra|cost|fee|charge)\b", q)
            and re.search(r"\bfee\b.{0,80}\binstallment\b|"
                          r"\binstallment\b.{0,80}\bfee\b", passage, re.I)
            and re.search(r"₱\s*\d", passage)):
        bonus += 5.0
    asks_return_amount = bool(
        re.search(r"\brefund\w*\b", q)
        or (re.search(r"\b(?:come|comes|coming)\s+back\b|\bmoney\s+back\b|\breimburse\w*\b", q)
            and re.search(r"\bwithdraw\w*\b", q))
    )
    if (re.search(r"\bhow\s+much\b", q) and asks_return_amount
            and re.search(r"refund\w*.{0,20}\d+(?:\.\d+)?\s*%", passage, re.I)):
        bonus += 5.0
    asks_award_guarantee = bool(
        re.search(r"\b(?:guarantee|guaranteed|entitled)\w*\b", q)
        and re.search(r"\b(?:scholarship|award)\w*\b", q)
    )
    denies_automatic_award = bool(
        re.search(r"\bno\s+actual\s+award\b", passage, re.I)
        or re.search(r"\bno\s+actual\s+entitlement\b", passage, re.I)
    )
    if asks_award_guarantee and denies_automatic_award:
        bonus += 4.0
    return bonus


def _requests_unit_rate(question: str) -> bool:
    q = unicodedata.normalize("NFKC", question).casefold()
    query_terms = set(_tokens(question))
    return bool(
        (re.search(r"\b(?:tuition|cost|charge|rate|price)\b", q)
         or re.search(r"\bhow\s+much\b", q))
        and "unit" in query_terms
        and query_terms & {"per", "each", "one"}
    )


def _provides_unit_rate(passage: str) -> bool:
    return bool(re.search(
        r"₱\s*[0-9][0-9,]*(?:\.[0-9]+)?\s+per\s+unit\b"
        r"|\bper\s+unit\s+(?:costs?|is|equals?)\s+₱\s*[0-9]",
        passage, re.I,
    ))


def _unanchored_numeric_signal(term: str, passage: str) -> bool:
    """A number alone is not new evidence unless tied to a monetary value."""
    if not re.fullmatch(r"\d+(?:\.\d+)?", term):
        return False
    for match in re.finditer(rf"(?<!\w){re.escape(term)}(?!\w)", passage):
        nearby = passage[max(0, match.start() - 30):match.end() + 30]
        if re.search(r"₱|\bphp\b|%", nearby, re.IGNORECASE):
            return False
    return True


class KeywordRetriever:
    """Search fresh eligible chunks; keep a bounded, deterministic candidate set.

    Source failures propagate to the future service layer. They must become
    'unavailable', not be disguised as a successful search with no evidence.
    """

    def __init__(self, source: PublicChunkSource, *, limit: int = MAX_EVIDENCE_CHUNKS,
                 _diagnostics: Callable[[dict], None] | None = None):
        if type(limit) is not int or not 1 <= limit <= 5:
            raise ValueError("invalid_retrieval_limit")
        self.source = source
        self.limit = limit
        self._diagnostics = _diagnostics
        self._cached_chunks = None
        self._cached_features = None
        self._cached_document_frequency = None

    def retrieve(self, question: str, *, reference_date: date) -> tuple[Evidence, ...]:
        question = validate_question(question)
        if type(reference_date) is not date:
            raise ValueError("invalid_reference_date")
        # General policy stays searchable for first-person questions. Explicit
        # personal-record requests have no eligible source in this demo.
        if _is_personal_record_request(question):
            return ()
        chunks = self.source.public_chunks(reference_date=reference_date)
        if not chunks:
            return ()

        # Corpus statistics are derived exclusively from the source's current,
        # eligibility-filtered public chunks, never from excluded records.
        if chunks == self._cached_chunks:
            features = self._cached_features
            document_frequency = self._cached_document_frequency
        else:
            features = []
            document_frequency = Counter()
            for chunk in chunks:
                body_tokens = _passage_tokens(chunk.chunk_text)
                title_tokens = _tokens(chunk.title)
                body_set = set(body_tokens)
                title_set = set(title_tokens)
                document_frequency.update(body_set | title_set)
                features.append((chunk, body_tokens, title_tokens, body_set, title_set))
            # public_chunks() has just revalidated the complete source. Cache only
            # its immutable returned passages; a changed/revoked set invalidates
            # this derived, request-local scoring data on the next call.
            self._cached_chunks = chunks
            self._cached_features = tuple(features)
            self._cached_document_frequency = document_frequency
            features = self._cached_features

        question_clauses = _split_question_clauses(question)
        question_profiles = tuple(
            _prepare_profile(_query_profile(clause), document_frequency, len(chunks))
            for clause in question_clauses
        )
        context_profiles = tuple(
            _prepare_profile(
                _query_profile(" ".join((*question_clauses[:index], clause))),
                document_frequency, len(chunks),
            ) if index else None
            for index, clause in enumerate(question_clauses)
        )
        context_named_terms = tuple(
            _named_terms(" ".join(question_clauses[:index])) if index else frozenset()
            for index in range(len(question_clauses))
        )
        if not any(profile[0] for profile in question_profiles):
            return ()
        if self._diagnostics:
            self._diagnostics({
                "stage": "query",
                "tokens": list(_tokens(question, remove_stop_words=False)),
                "clauses": [list(_tokens(clause, remove_stop_words=False))
                            for clause in question_clauses],
                "intent_signals": {
                    "clock_time": bool(re.search(r"\b(?:what\s+time|time)\b", question, re.I)),
                    "location": bool(re.search(r"\b(?:where|venue|location|held)\b", question, re.I)),
                    "date_or_deadline": bool(re.search(r"\b(?:when|date|deadline|due)\b", question, re.I)),
                    "money_amount": bool(re.search(r"\b(?:how\s+much|amount|price|fee|cost|total)\b", question, re.I)),
                    "refund_amount": bool(re.search(r"\brefund\w*\b|\b(?:come|comes)\s+back\b|\bmoney\s+back\b", question, re.I)),
                    "comparison": bool(re.search(r"\b(?:compare|compared|versus|vs\.?|than)\b", question, re.I)),
                    "role_or_responsibility": bool(re.search(r"\bwho\b", question, re.I)
                                                    and re.search(r"\b(?:check|verify|confirm)\w*\b", question, re.I)),
                },
                "profiles": [{
                    "normalized_terms": sorted(profile[1]),
                    "weighted_terms": [[term, weight, round(idf, 5)]
                                       for term, weight, idf in profile[0]],
                    "phrases": [list(phrase) for phrase in profile[2]],
                    "expanded_terms": sorted(profile[3]),
                    "named_terms": sorted(profile[4]),
                } for profile in question_profiles],
                "context_profiles": [{
                    "context_terms": sorted({term for term, *_ in profile[0]}
                                             - {term for term, *_ in question_profiles[index][0]}),
                    "context_named_terms": sorted(context_named_terms[index]),
                    "context_expanded_terms": sorted(profile[3]),
                } if profile else None
                    for index, profile in enumerate(context_profiles)],
            })

        candidates = []
        for chunk, body_tokens, title_tokens, body_set, title_set in features:
            clause_scores = []
            clause_matches = []
            qualified_clauses = set()
            candidate_phrase_bonus = 0.0
            candidate_coverage = 0.0
            clause_diagnostics = []
            for clause_index, profile in enumerate(question_profiles):
                (score, body_matches, title_matches, coverage,
                 phrase_bonus, named_coverage) = _score_profile(
                    profile, body_tokens, title_tokens, body_set, title_set,
                )
                numeric_bonus = _numeric_answer_bonus(
                    question_clauses[clause_index], chunk.chunk_text,
                )
                date_bonus = _dated_event_bonus(
                    question_clauses[clause_index], chunk.chunk_text, body_set,
                )
                attribute_bonus = _event_attribute_bonus(
                    question_clauses[clause_index], chunk.chunk_text, question,
                )
                answer_type_bonus = _answer_type_bonus(
                    question_clauses[clause_index], chunk.chunk_text,
                )
                context_profile = context_profiles[clause_index]
                context_bonus = 0.0
                context_name_match = True
                if context_profile:
                    base_terms = {term for term, *_ in profile[0]}
                    context_matches = [
                        (term, weight, idf)
                        for term, weight, idf in context_profile[0]
                        if term not in base_terms and term in body_set
                    ]
                    context_bonus = min(1.5, sum(weight * idf for _, weight, idf
                                                 in context_matches) * 0.15)
                    previous_names = context_named_terms[clause_index]
                    comparison_intent = bool(re.search(
                        r"\b(?:compare|compared|comparison|versus|vs\.?|than)\b",
                        question_clauses[clause_index], re.IGNORECASE,
                    ))
                    context_name_match = previous_names <= body_set or comparison_intent
                (_weighted_terms, original_terms, _phrases, expansion_terms,
                 named_terms, _denominator) = profile
                expansion_matches = sum(term in body_set for term in expansion_terms)
                role_intent = bool(
                    re.search(r"\bwho\b", question_clauses[clause_index], re.IGNORECASE)
                    and re.search(r"\b(?:check|verify|confirm)\w*\b",
                                  question_clauses[clause_index], re.IGNORECASE)
                )
                complementary_role_evidence = role_intent and expansion_matches >= 2
                score += numeric_bonus + date_bonus + attribute_bonus + answer_type_bonus + context_bonus
                qualified = _candidate_is_relevant(
                    score, body_matches, coverage,
                    phrase_bonus + numeric_bonus + date_bonus + attribute_bonus
                    + answer_type_bonus + context_bonus,
                    expansion_matches,
                    named_coverage,
                    named_terms,
                    original_terms,
                )
                if not context_name_match and not complementary_role_evidence:
                    qualified = False
                enrollment_date_query = bool(
                    re.search(r"\b(?:enrollment|enroll|registration|register)\b",
                              question_clauses[clause_index], re.IGNORECASE)
                    and re.search(r"\b(?:when|date|first|open|opening|until|deadline|close|closes)\b",
                                  question_clauses[clause_index], re.IGNORECASE)
                )
                if enrollment_date_query and not body_set & {"enrollment", "registration"}:
                    qualified = False
                if self._diagnostics:
                    clause_diagnostics.append({
                        "clause_index": clause_index,
                        "weighted_matches": [
                            {"term": term, "weight": weight, "idf": round(idf, 5),
                             "body_contribution": round(idf * weight if term in body_set else 0.0, 5),
                             "title_contribution": round(idf * weight * TITLE_WEIGHT
                                                          if term not in body_set and term in title_set
                                                          else 0.0, 5)}
                            for term, weight, idf in profile[0]
                            if term in body_set or term in title_set
                        ],
                        "body_matches": sorted(body_matches),
                        "title_matches": sorted(title_matches),
                        "phrase_bonus": phrase_bonus,
                        "numeric_bonus": numeric_bonus,
                        "date_bonus": date_bonus,
                        "event_attribute_bonus": attribute_bonus,
                        "answer_type_bonus": answer_type_bonus,
                        "context_bonus": context_bonus,
                        "context_name_match": context_name_match,
                        "expansion_match_count": expansion_matches,
                        "named_coverage": named_coverage,
                        "score": round(score, 5),
                        "qualified": qualified,
                    })
                if qualified:
                    qualified_clauses.add(clause_index)
                clause_scores.append(score)
                clause_matches.append(
                    body_matches | title_matches
                    | frozenset(term for term in expansion_terms if term in body_set)
                )
                candidate_phrase_bonus = max(candidate_phrase_bonus, phrase_bonus)
                candidate_coverage = max(candidate_coverage, coverage)

            if not qualified_clauses:
                if self._diagnostics:
                    self._diagnostics({
                        "stage": "candidate", "document_id": chunk.document_id,
                        "page_no": chunk.page_no, "accepted": False,
                        "clauses": clause_diagnostics,
                    })
                continue
            matched_terms = frozenset().union(*clause_matches)
            signal_weights = {}
            for profile in question_profiles:
                for term, weight, _idf in profile[0]:
                    signal_weights[term] = max(signal_weights.get(term, 0.0), weight)
            signal_matches = frozenset(
                term for term in signal_weights if term in body_set
            )
            combined_score = sum(clause_scores)
            program_bonus = _program_list_bonus(question, chunk.chunk_text)
            candidates.append({
                "chunk": chunk,
                "score": combined_score + program_bonus,
                "program_bonus": program_bonus,
                "clause_scores": tuple(clause_scores),
                "qualified_clauses": frozenset(qualified_clauses),
                "matched_terms": matched_terms,
                "signal_matches": signal_matches,
                "signal_weights": signal_weights,
                "phrase_bonus": candidate_phrase_bonus,
                "coverage": candidate_coverage,
            })
            if self._diagnostics:
                self._diagnostics({
                    "stage": "candidate", "document_id": chunk.document_id,
                    "page_no": chunk.page_no, "accepted": True,
                    "clauses": clause_diagnostics,
                })

        if not candidates:
            return ()

        def order(candidate):
            chunk = candidate["chunk"]
            return (
                -len(candidate["qualified_clauses"]),
                -candidate["score"],
                -candidate["phrase_bonus"],
                -candidate["coverage"],
                chunk.document_id,
                chunk.page_no,
                chunk.chunk_index,
            )

        candidates.sort(key=order)
        if self._diagnostics:
            self._diagnostics({
                "stage": "ranked_candidates",
                "items": [{
                    "document_id": item["chunk"].document_id,
                    "page_no": item["chunk"].page_no,
                    "score": round(item["score"], 5),
                    "program_bonus": item["program_bonus"],
                    "qualified_clauses": sorted(item["qualified_clauses"]),
                    "matched_terms": sorted(item["matched_terms"]),
                } for item in candidates],
            })
        max_results = min(self.limit, MAX_EVIDENCE_CHUNKS)
        selected = []
        covered_clauses = set()
        clause_selection_decisions = []

        # Greedily cover each clear question component. A single passage that
        # covers both components is preferred and remains a one-chunk answer.
        for clause_index in range(len(question_profiles)):
            if clause_index in covered_clauses or len(selected) >= max_results:
                clause_selection_decisions.append({
                    "clause_index": clause_index, "decision": "already_covered_or_budget",
                })
                continue
            options = [item for item in candidates
                       if clause_index in item["qualified_clauses"]]
            if not options:
                clause_selection_decisions.append({
                    "clause_index": clause_index, "decision": "no_qualified_candidate",
                })
                continue
            def clause_order(item):
                chunk = item["chunk"]
                return (
                    -(item["clause_scores"][clause_index] + item["program_bonus"]),
                    -item["phrase_bonus"],
                    -item["coverage"],
                    chunk.document_id,
                    chunk.page_no,
                    chunk.chunk_index,
                )

            best = min(options, key=clause_order)
            selection_item = {
                "clause_index": clause_index,
                "document_id": best["chunk"].document_id,
                "page_no": best["chunk"].page_no,
                "clause_score": round(best["clause_scores"][clause_index], 5),
            }
            if best not in selected:
                proposed = tuple(selected + [best])
                if (len(proposed) <= MAX_EVIDENCE_CHUNKS
                        and sum(len(item["chunk"].chunk_text) for item in proposed)
                        <= MAX_EVIDENCE_CHARS):
                    selected.append(best)
                    selection_item["decision"] = "selected"
                else:
                    selection_item["decision"] = "evidence_budget"
            else:
                selection_item["decision"] = "already_selected_for_another_clause"
            clause_selection_decisions.append(selection_item)
            if best in selected:
                covered_clauses.update(best["qualified_clauses"])

        # For a single clause, a second passage is admitted only when it adds a
        # new, substantive original-query term. This suppresses weak and
        # duplicate pages without eliminating complementary two-part evidence.
        if len(question_profiles) == 1 and selected and len(selected) < max_results:
            covered_terms = set().union(*(item["signal_matches"] for item in selected))
            selected_documents = {item["chunk"].document_id for item in selected}
            detail_intent = bool(set(_tokens(question)) & {
                "explain", "detail", "details", "step", "steps", "procedure",
                "procedures", "list", "all",
            })
            secondary_decisions = []
            for candidate in candidates:
                if candidate in selected:
                    secondary_decisions.append({
                        "document_id": candidate["chunk"].document_id,
                        "page_no": candidate["chunk"].page_no,
                        "decision": "already_selected",
                    })
                    continue
                if (_requests_unit_rate(question)
                        and not _provides_unit_rate(candidate["chunk"].chunk_text)):
                    secondary_decisions.append({
                        "document_id": candidate["chunk"].document_id,
                        "page_no": candidate["chunk"].page_no,
                        "decision": "does_not_match_requested_unit_rate",
                    })
                    continue
                new_terms = {
                    term for term in candidate["signal_matches"] - covered_terms
                    if candidate["signal_weights"].get(term, 0.0) >= 0.4
                    and not _unanchored_numeric_signal(term, candidate["chunk"].chunk_text)
                }
                new_weight = sum(candidate["signal_weights"].get(term, 0.0)
                                 for term in new_terms)
                required_new_terms = (
                    1 if candidate["chunk"].document_id in selected_documents and detail_intent
                    else 2
                )
                if len(new_terms) < required_new_terms or new_weight < 0.8:
                    secondary_decisions.append({
                        "document_id": candidate["chunk"].document_id,
                        "page_no": candidate["chunk"].page_no,
                        "decision": "insufficient_new_query_signal",
                        "new_terms": sorted(new_terms),
                        "new_weight": round(new_weight, 5),
                    })
                    continue
                proposed = tuple(selected + [candidate])
                if (len(proposed) <= MAX_EVIDENCE_CHUNKS
                        and sum(len(item["chunk"].chunk_text) for item in proposed)
                        <= MAX_EVIDENCE_CHARS):
                    selected.append(candidate)
                    secondary_decisions.append({
                        "document_id": candidate["chunk"].document_id,
                        "page_no": candidate["chunk"].page_no,
                        "decision": "selected_complementary_signal",
                        "new_terms": sorted(new_terms),
                        "new_weight": round(new_weight, 5),
                    })
                    selected_documents.add(candidate["chunk"].document_id)
                    covered_terms.update(candidate["signal_matches"])
                    if len(selected) >= max_results:
                        break
            if self._diagnostics:
                self._diagnostics({
                    "stage": "secondary_selection",
                    "decisions": secondary_decisions,
                })

        if self._diagnostics:
            self._diagnostics({
                "stage": "final_selection",
                "clause_decisions": clause_selection_decisions,
                "items": [{"document_id": item["chunk"].document_id,
                           "page_no": item["chunk"].page_no}
                          for item in selected],
            })

        return tuple(
            Evidence(
                f"e{index}", item["chunk"], tuple(sorted(item["matched_terms"])),
            )
            for index, item in enumerate(selected, start=1)
        )
