"""Small extractive answering service: model-selected quotes, backend checks.

Exact quote checks prevent newly invented wording, but cannot prove that a quote
answers the question or preserves all necessary context. This is not a semantic
verifier, production authorization system, or complete injection defense.
"""

import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai.local_retrieval import (
    Evidence, Retriever, _passage_tokens, _tokens,
    validate_question, validate_evidence_budget,
)
from ai.llm_client import DiagnosticFailure, diagnostic_event, diagnostic_request


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SupportingQuote(StrictModel):
    evidence_id: str = Field(min_length=1, max_length=20)
    quote: str = Field(min_length=1, max_length=300)


class CoveragePart(StrictModel):
    part_index: int = Field(ge=1, le=2)
    part_text: str = Field(min_length=1, max_length=2000)
    support: Literal["supported", "unsupported"]
    answer_text: str | None = Field(min_length=1, max_length=1200)
    evidence: list[SupportingQuote] = Field(max_length=2)


class ModelSelection(StrictModel):
    status: Literal["answered", "insufficient_evidence"]
    parts: list[CoveragePart] = Field(max_length=2)


class Citation(StrictModel):
    evidence_id: str
    document_id: int
    page_no: int
    chunk_index: int
    title: str
    version: str
    source_reference: str


class AnswerResponse(StrictModel):
    status: Literal["answered", "insufficient_evidence", "unavailable", "denied"]
    answer: str = Field(min_length=1, max_length=4000)
    citations: list[Citation] = Field(max_length=3)
    fictional: Literal[True] = True


MESSAGES = {
    "insufficient_evidence": "The fictional demo documents do not provide enough verified information to answer this question.",
    "unavailable": "The fictional demo cannot verify an answer right now. Please try again later.",
    "denied": "This public fictional demo cannot provide that information.",
}


def fallback(status: Literal["insufficient_evidence", "unavailable", "denied"]) -> AnswerResponse:
    return AnswerResponse(status=status, answer=MESSAGES[status], citations=[])


class AnswerGenerator(Protocol):
    def generate(self, question: str, evidence: tuple[Evidence, ...]) -> str:
        """Return structured JSON, never trusted user-facing output."""
        ...


def _unique_json_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("invalid_model_output")
        result[key] = value
    return result


def _answer_question_parts(question: str) -> tuple[str, ...]:
    """Split only explicit conjunctive requests; commas inside conditions are not new parts."""
    pieces = re.split(
        r";\s*|\band\s+(?=(?:when|what|who|where|how|which|whether|can|does|do|is)\b)",
        question, maxsplit=2, flags=re.IGNORECASE,
    )
    parts = tuple(piece.strip(" ,;?") for piece in pieces if piece.strip(" ,;?"))
    if len(parts) > 2 or not parts or not all(_tokens(part) for part in parts):
        return ()
    return parts


class IncompleteAnswer(ValueError):
    """Valid provider structure that lacks relevant or complete support."""


_ANSWER_CONNECTORS = frozenset({
    "a", "about", "according", "after", "all", "also", "an", "and", "are",
    "as", "at", "based", "before", "by", "can", "conditional", "demo",
    "each", "estimated", "fictional", "for", "from", "if", "in", "includes",
    "is", "it", "may", "not", "of", "on", "only", "or", "per", "please",
    "provided", "simulated", "so", "that", "the", "then", "this", "to", "under",
    "use", "using", "with", "would", "available", "required",
})
_ANSWER_TOKEN_EQUIVALENTS = {
    "used": "use", "uses": "use", "using": "use",
    "reviews": "review", "reviewed": "review", "reviewing": "review",
    "handles": "support", "handle": "support", "handled": "support",
    "contacts": "email", "contact": "email",
    "failing": "fail", "failed": "fail", "fails": "fail",
    "lists": "list", "listed": "list",
    "requires": "require", "required": "require",
    "submitted": "submit", "submits": "submit",
    "fee": "financial_amount", "fees": "financial_amount", "cost": "financial_amount",
    "costs": "financial_amount", "charge": "financial_amount", "charges": "financial_amount",
    "price": "financial_amount", "amount": "financial_amount",
}
_HIGH_RISK_NUMBER_RE = re.compile(
    r"(?<![A-Za-z])(?:₱\s*|PHP\s*)?\d[\d,]*(?:\.\d+)?%?",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2}(?:,\s*\d{4})?\b", re.IGNORECASE,
)
_TIME_RE = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?|noon)\b", re.I)
_CURRENCY_RE = re.compile(r"(?:₱\s*|\bPHP\s*)\d[\d,]*(?:\.\d{1,2})?", re.I)


def _money(value: str) -> Decimal:
    return Decimal(value.replace(",", "")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_money(value: Decimal) -> str:
    value = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if value == value.to_integral_value():
        return f"₱{int(value):,}"
    return f"₱{value:,.2f}"


def _citation_list(evidence: tuple[Evidence, ...], evidence_ids: set[str]) -> list[Citation]:
    citations = []
    for item in evidence:
        if item.evidence_id in evidence_ids and item.chunk.version:
            citations.append(Citation(
                evidence_id=item.evidence_id, document_id=item.chunk.document_id,
                page_no=item.chunk.page_no, chunk_index=item.chunk.chunk_index,
                title=item.chunk.title, version=item.chunk.version,
                source_reference=item.chunk.source_reference,
            ))
    return citations


def _render_answer(texts: list[str], citations: list[Citation]) -> AnswerResponse:
    if len(texts) == 1:
        body = texts[0]
    else:
        body = "\n".join(f"{index}. {text}" for index, text in enumerate(texts, 1))
    answer = ("Based on fictional Demo Campus University documents:\n" + body
              + "\n\nThis is fictional demonstration information, not official university policy.")
    return AnswerResponse(status="answered", answer=answer, citations=citations)


def _source_quote_is_relevant(question: str, quote: str) -> bool:
    source_terms = {_ANSWER_TOKEN_EQUIVALENTS.get(term, term) for term in _passage_tokens(quote)}
    question_terms = set(_tokens(question)) - {"available", "current", "first", "next", "day", "term"}
    question_terms = {_ANSWER_TOKEN_EQUIVALENTS.get(term, term) for term in question_terms}
    return bool(question_terms & source_terms)


def _covered_answer_type(question: str, quotes: list[str]) -> bool:
    """Conservative checks for common requested fact types; not a semantic parser."""
    q = question.casefold()
    text = " ".join(quotes)
    if re.search(r"\b(?:when|date|deadline|due|until|open|start|begin)\b", q):
        if not _DATE_RE.search(text):
            return False
    if re.search(r"\b(?:what\s+time|at\s+what\s+time)\b", q) and not _TIME_RE.search(text):
        return False
    if re.search(r"\b(?:time\s+does|what\s+time)\b", q) and not _TIME_RE.search(text):
        return False
    if re.search(r"\b(?:where|venue|location|which\s+room)\b", q):
        if not re.search(r"\b(?:at|in|to)\s+(?:the\s+)?(?:[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,3}|Registrar|Student Affairs)\b", text):
            return False
    if re.search(r"\b(?:how\s+long|processing\s+time|working\s+days?|calendar\s+days?)\b", q):
        if not re.search(r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:working\s+|calendar\s+)?days?\b", text, re.I):
            return False
    if re.search(r"\b(?:how\s+much|cost|price|fee|fees|charge|charges|amount|tuition|assessment)\b", q):
        if not _CURRENCY_RE.search(text) and not re.search(r"\b\d+(?:\.\d+)?\s*%", text):
            return False
    if re.search(r"\bGPA\b", q, re.I) and not re.search(r"\bGPA\b", text, re.I):
        return False
    if re.search(r"\bfailed\s+courses?\b", q, re.I) and not re.search(r"\bno\s+failed\s+courses?\b", text, re.I):
        return False
    if re.search(r"\b(?:automatic(?:ally)?\s+fail|fail\s+automatically)\b", q, re.I) and not re.search(
            r"\bnot\s+(?:impose|cause)\b.{0,80}\bfail\w*\b", text, re.I):
        return False
    if re.search(r"\b(?:unit|units|course\s+load|academic\s+load|credit|credits)\b", q, re.I):
        if not re.search(r"\bunits?\b", text, re.I):
            return False
    if re.search(r"\b(?:prerequisite|pre-requisite)\b", q) and not re.search(
            r"\b(?:prerequisite|requires?\s+passing|verify\s+prerequisites?)\b", text, re.I):
        return False
    if re.search(r"\b(?:who|which\s+office|responsible)\b", q) and not re.search(
            r"\b(?:Registrar|Office|advisers?|advisors?|Student Affairs|Finance)\b", text, re.I):
        return False
    if re.search(r"\b(?:contact|email|how\s+can\s+i\s+reach)\b", q) and not re.search(
            r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text):
        return False
    if re.search(r"\blibrary\b", q) and re.search(r"\b(?:hours?|open|close|time)\b", q):
        if not any(re.search(r"\blibrary\b", quote, re.I) and _TIME_RE.search(quote)
                   for quote in quotes):
            return False
    if re.search(r"\bfixed\s+(?:(?:academic|school|institutional)\s+)?(?:fees?|charges?)\b", q) and re.search(
            r"\b(?:which|what|list|breakdown|categories|make\s+up)\b", q):
        items = ("registration", "library", "technology", "student services")
        if not all(term in text.casefold() for term in items):
            return False
    if re.search(r"\b(?:course\s+plan|enrollment\s+procedure)\b", q):
        if not re.search(r"\bcourse\s+plan\b", text, re.I):
            return False
    if re.search(r"\b(?:guarantee|guaranteed|entitled|entitlement)\b", q):
        if not re.search(r"\bno\s+actual\s+(?:award|entitlement)\b", text, re.I):
            return False
    eligibility_query = bool(
        re.search(r"\b(?:Lakbay|Access\s+Support|Community\s+Service)\b", question, re.I)
        and re.search(r"\b(?:GPA|units?|eligibility|eligible|qualify|requirements?)\b", q, re.I)
        and not re.search(r"\b(?:guarantee|guaranteed|entitled|entitlement)\b", q)
    )
    if eligibility_query:
        if re.search(r"\bLakbay\b", question, re.I) and not re.search(r"\bno\s+failed\s+courses?\b", text, re.I):
            return False
        if re.search(r"\bAccess\s+Support\b", question, re.I) and not re.search(
                r"household[-\s]+income", text, re.I):
            return False
        if re.search(r"\bCommunity\s+Service\b", question, re.I) and not re.search(
                r"\b\d+\s+(?:prior[-\s]+term\s+)?service\s+hours?\b", text, re.I):
            return False
    return True


def _answer_contains_requested_facts(question: str, answer_text: str) -> bool:
    q = question.casefold()
    answer = answer_text.casefold()
    if (re.search(r"\b(?:enrollment|enroll|registration|register)\b", q)
            and re.search(r"\b(?:when|date|deadline|due|until|open|opening|close|closes|start|first)\b", q)):
        if not re.search(r"\b(?:enrollment|enroll\w*|registration|register\w*)\b", answer):
            return False
        if re.search(r"\b(?:open|opening|available)\b", q) and not re.search(r"\b(?:open\w*|available)\b", answer):
            return False
        if re.search(r"\b(?:close|closes|deadline|until|last\s+day)\b", q) and not re.search(
                r"\b(?:close\w*|deadline|last\s+day|through|ends?)\b", answer):
            return False
    if re.search(r"\badd\s*/\s*drop\b", q) and re.search(r"\b(?:when|date|end|until)\b", q):
        if not re.search(r"\badd\s*/\s*drop\b", answer):
            return False
    if re.search(r"\bclasses?\b", q) and re.search(r"\b(?:when|day|start|begin)\b", q):
        if not re.search(r"\bclasses?\b", answer):
            return False
    if re.search(r"\b(?:when|date|deadline|due|until|open|start|begin)\b", q) and not _DATE_RE.search(answer):
        return False
    if re.search(r"\b(?:what\s+time|at\s+what\s+time)\b", q) and not _TIME_RE.search(answer):
        return False
    if re.search(r"\b(?:where|venue|location|which\s+room)\b", q) and not re.search(
            r"\b(?:at|in|to)\s+(?:the\s+)?(?:[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,3})", answer_text):
        return False
    if re.search(r"\b(?:how\s+long|processing\s+time|working\s+days?|calendar\s+days?)\b", q) and not re.search(
            r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:working\s+|calendar\s+)?days?\b", answer, re.I):
        return False
    if re.search(r"\b(?:how\s+much|cost|price|fee|fees|charge|charges|amount|tuition|assessment)\b", q) and not (
            _CURRENCY_RE.search(answer_text) or re.search(r"\b\d+(?:\.\d+)?\s*%", answer)):
        return False
    if re.search(r"\bGPA\b", q, re.I):
        if not re.search(r"\bGPA\b", answer, re.I) or not re.search(r"\b\d\.\d{1,2}\b", answer):
            return False
    unit_rate = bool(re.search(r"\b(?:per|each|one)\b", q)
                     and re.search(r"\b(?:unit|credit)\b", q)
                     and re.search(r"\b(?:tuition|rate|cost|charge|price|how\s+much)\b", q))
    if unit_rate and (not _CURRENCY_RE.search(answer_text) or not re.search(r"\bper\s+unit\b", answer)):
        return False
    if re.search(r"\b(?:minimum|at\s+least|how\s+many|unit\s+load)\b", q) and re.search(r"\bunits?\b", q):
        if not re.search(r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+units?\b", answer):
            return False
    if re.search(r"\bfailed\s+courses?\b", q, re.I) and not re.search(r"\bno\s+failed\s+courses?\b", answer, re.I):
        return False
    if re.search(r"\b(?:automatic(?:ally)?\s+fail|fail\s+automatically)\b", q, re.I) and not re.search(
            r"\bnot\s+(?:impose|cause)\b.{0,80}\bfail\w*\b", answer, re.I):
        return False
    if re.search(r"\b(?:which|what|list|breakdown|categories|make\s+up)\b", q) and re.search(
            r"\bfixed\s+(?:(?:academic|school|institutional)\s+)?(?:fees?|charges?)\b", q):
        if not all(term in answer for term in ("registration", "library", "technology", "student services")):
            return False
    if re.search(r"\b(?:contact|email|how\s+can\s+i\s+reach)\b", q) and not re.search(
            r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", answer):
        return False
    if re.search(r"\b(?:submit|procedure|steps?|how\s+do\s+i|how\s+to|apply\s+for|application\s+process)\b", q):
        if not re.search(r"\b(?:submit|send|apply|request|select|prepare|receive|contact)\w*\b", answer):
            return False
    if re.search(r"\b(?:guarantee|guaranteed|entitled|entitlement)\b", q):
        if not re.search(r"\bno\b", answer) or not re.search(r"\b(?:award|entitlement)\b", answer):
            return False
    eligibility_query = bool(
        re.search(r"\b(?:Lakbay|Access\s+Support|Community\s+Service)\b", question, re.I)
        and re.search(r"\b(?:GPA|units?|eligibility|eligible|qualify|requirements?)\b", q, re.I)
        and not re.search(r"\b(?:guarantee|guaranteed|entitled|entitlement)\b", q)
    )
    if eligibility_query:
        if re.search(r"\bLakbay\b", question, re.I) and not re.search(r"\bno\s+failed\s+courses?\b", answer, re.I):
            return False
        if re.search(r"\bAccess\s+Support\b", question, re.I) and not re.search(r"household[-\s]+income", answer, re.I):
            return False
        if re.search(r"\bCommunity\s+Service\b", question, re.I) and not re.search(
                r"\b\d+\s+(?:prior[-\s]+term\s+)?service\s+hours?\b", answer, re.I):
            return False
    if re.search(r"\b(?:if|hypothetical|assuming)\b", q) and re.search(r"\b(?:scholarship|award)\b", q):
        if not re.search(r"\b(?:if|conditional)\b", answer):
            return False
    return True


def _validate_answer_text(answer_text: str, question: str, quotes: list[str]) -> None:
    covered_type = _covered_answer_type(question, quotes)
    if not covered_type:
        raise IncompleteAnswer("answer_missing_requested_fact_type")

    source_text = " ".join(quotes)
    source_terms = {_ANSWER_TOKEN_EQUIVALENTS.get(term, term) for term in _passage_tokens(source_text)}
    answer_terms = {_ANSWER_TOKEN_EQUIVALENTS.get(term, term) for term in _tokens(answer_text)}
    unsupported_terms = answer_terms - source_terms - _ANSWER_CONNECTORS
    if unsupported_terms:
        raise IncompleteAnswer("answer_contains_unanchored_terms")
    if not _answer_contains_requested_facts(question, answer_text):
        raise IncompleteAnswer("answer_omits_requested_fact")
    if _conflicting_evidence_values(question, quotes):
        raise IncompleteAnswer("answer_evidence_conflicts")
    question_terms = {_ANSWER_TOKEN_EQUIVALENTS.get(term, term) for term in _tokens(question)}
    direct_relevance = bool(question_terms & source_terms)
    answer_bridge = bool(question_terms & answer_terms & source_terms)
    typed_intent = bool(re.search(
        r"\b(?:when|date|deadline|due|until|open|start|begin|where|venue|location|"
        r"what\s+time|how\s+long|processing\s+time|how\s+much|cost|price|fee|fees|"
        r"charge|charges|amount|tuition|assessment|contact|email|GPA|units?|prerequisite)\b",
        question, re.I,
    ))
    if not direct_relevance and not answer_bridge and not typed_intent:
        raise IncompleteAnswer("answer_evidence_not_relevant")

    if re.search(r"\b(?:you\s+(?:qualify|are\s+eligible|will\s+receive)|approved\s+for\s+your\s+award)\b",
                 answer_text, re.I):
        raise IncompleteAnswer("answer_claims_personal_eligibility")

    source_values = {value.replace(",", "").rstrip("%") for value in
                     _HIGH_RISK_NUMBER_RE.findall(source_text)}
    number_text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", answer_text)
    answer_values = {value.replace(",", "").rstrip("%") for value in
                     _HIGH_RISK_NUMBER_RE.findall(number_text)}
    if not answer_values <= source_values:
        raise IncompleteAnswer("answer_contains_unanchored_number")
    if any(not re.search(re.escape(value), source_text, re.I)
           for value in _DATE_RE.findall(answer_text)):
        raise IncompleteAnswer("answer_contains_unanchored_date")


def _conflicting_evidence_values(question: str, quotes: list[str]) -> bool:
    text = " ".join(quotes)
    q = question.casefold()
    rate_query = bool(re.search(r"\b(?:tuition|cost|charge|rate|price|how\s+much)\b", q)
                      and re.search(r"\b(?:per|each|one)\b", q)
                      and re.search(r"\b(?:unit|credit)\b", q))
    if rate_query:
        rates = {_money(match.group(1)) for match in re.finditer(
            r"₱\s*([\d,]+(?:\.\d{1,2})?)\s+per\s+(?:academic\s+)?unit\b", text, re.I)}
        if len(rates) > 1:
            return True
    if re.search(r"\btotal\s+fixed\s+(?:fees?|charges?)\b", q):
        totals = {_money(match.group(1)) for match in re.finditer(
            r"total\s+fixed\s+charges\s*₱\s*([\d,]+(?:\.\d{1,2})?)", text, re.I)}
        if len(totals) > 1:
            return True
    for award in re.findall(r"\b(?:Lakbay|Access\s+Support|Community\s+Service)\b", question, re.I):
        thresholds = set()
        for quote in quotes:
            for match in re.finditer(re.escape(award), quote, re.I):
                context = quote[max(0, match.start() - 40):match.end() + 180]
                thresholds.update(re.findall(
                    r"GPA\s+(?:must\s+not\s+exceed|is|of)?\s*(\d\.\d{1,2})", context, re.I,
                ))
        if len(thresholds) > 1:
            return True
    return False


def _extract_unique_money(evidence: tuple[Evidence, ...], pattern: re.Pattern) -> tuple[Decimal, set[str]] | None:
    found: dict[Decimal, set[str]] = {}
    for item in evidence:
        for match in pattern.finditer(item.chunk.chunk_text):
            try:
                value = _money(match.group(1))
            except (InvalidOperation, ValueError):
                continue
            found.setdefault(value, set()).add(item.evidence_id)
    if len(found) != 1:
        return None
    value, evidence_ids = next(iter(found.items()))
    return value, evidence_ids


def _fixed_charge_data(evidence: tuple[Evidence, ...]):
    totals = _extract_unique_money(evidence, re.compile(r"total\s+fixed\s+charges\s*₱\s*([\d,]+(?:\.\d{1,2})?)", re.I))
    if totals is None:
        return None
    total, ids = totals
    charges = {}
    charge_pattern = re.compile(r"fixed\s+charges\s*:\s*(.*?);\s*total\s+fixed\s+charges", re.I | re.S)
    item_pattern = re.compile(r"([A-Za-z][A-Za-z ]{1,40}?)\s+₱\s*([\d,]+(?:\.\d{1,2})?)")
    for item in evidence:
        match = charge_pattern.search(item.chunk.chunk_text)
        if not match:
            continue
        local = {}
        for label, amount in item_pattern.findall(match.group(1)):
            try:
                local[label.strip()] = _money(amount)
            except (InvalidOperation, ValueError):
                return None
        if local:
            if charges and charges != local:
                return None
            charges = local
            ids.add(item.evidence_id)
    if not charges or sum(charges.values(), Decimal("0.00")) != total:
        return None
    return charges, total, ids


def deterministic_financial_answer(question: str, evidence: tuple[Evidence, ...]) -> AnswerResponse | None:
    """Render only calculations whose operands and conditions occur in supplied evidence."""
    answer_parts = _answer_question_parts(question)
    if not answer_parts or len(answer_parts) > 1:
        return None
    q = question.casefold()
    requests_breakdown = bool(
        re.search(r"\bfixed\s+(?:(?:academic|school|institutional)\s+)?(?:fees?|charges?)\b", q)
        and re.search(r"\b(?:which|what|list|breakdown|categories|make\s+up)\b", q)
    )
    requests_fixed_total = bool(
        re.search(r"\btotal\s+fixed\s+(?:(?:academic|school|institutional)\s+)?(?:fees?|charges?)\b", q)
        and not re.search(r"\bunits?\b", q)
    )
    if requests_breakdown or requests_fixed_total:
        data = _fixed_charge_data(evidence)
        if data is None:
            return fallback("insufficient_evidence")
        charges, total, evidence_ids = data
        if requests_breakdown:
            lines = [f"{label.strip().capitalize()}: {_format_money(amount)}" for label, amount in charges.items()]
            text = "The fictional fixed charges are " + "; ".join(lines) + f". Total fixed charges: {_format_money(total)}."
        else:
            text = f"The fictional total fixed charges are {_format_money(total)}."
        return _render_answer([text], _citation_list(evidence, evidence_ids))

    units_match = re.search(r"(?<![\w.])(-?\d+(?:\.\d+)?)[\s-]*(?:academic\s+)?units?\b", question, re.I)
    asks_units = bool(re.search(r"\b(?:units?|course\s+load)\b", q))
    asks_unit_rate = bool(
        re.search(r"\b(?:per|each|one)\b", q)
        and re.search(r"\b(?:unit|credit)\b", q)
        and re.search(r"\b(?:tuition|rate|cost|charge|price|how\s+much)\b", q)
    )
    if units_match is None and asks_unit_rate:
        asks_units = False
    financial_intent = bool(re.search(
        r"\b(?:tuition|assessment|bill|estimate|estimated|total|cost|how\s+much)\b", q,
    ))
    asks_installments = bool(re.search(r"\binstallments?\b", q)
                             and (re.search(r"\b(?:how\s+much|amounts?|calculate|split)\b", q)
                                  or _CURRENCY_RE.search(question)
                                  or re.search(r"\b(?:assessment|balance)\b", q)))
    asks_computation = (financial_intent and asks_units) or asks_installments
    if not asks_computation:
        return None

    if units_match:
        try:
            units_decimal = Decimal(units_match.group(1))
        except InvalidOperation:
            return fallback("insufficient_evidence")
        if (units_decimal <= 0 or units_decimal > 1000
                or units_decimal != units_decimal.to_integral_value()):
            return fallback("insufficient_evidence")
        units = int(units_decimal)
    elif asks_units:
        # A load estimate with a missing or spelled-out unit count cannot be independently calculated.
        return fallback("insufficient_evidence")
    else:
        units = None

    rate_pattern = re.compile(r"₱\s*([\d,]+(?:\.\d{1,2})?)\s+per\s+(?:academic\s+)?unit\b", re.I)
    rate = _extract_unique_money(evidence, rate_pattern)
    if units is not None and rate is None:
        return fallback("insufficient_evidence")
    tuition = rate[0] * units if rate and units is not None else None
    evidence_ids = set(rate[1]) if rate else set()
    charges_requested = bool(re.search(
        r"\b(?:total|assessment|bill|fixed\s+(?:fees?|charges?)|with\s+(?:all\s+)?fees?)\b", q,
    ) and not re.search(r"\b(?:excluding|exclude|without|tuition\s+only|tuition\s+alone)\b", q))
    charges = _fixed_charge_data(evidence) if charges_requested else None

    discount_requested = bool(
        re.search(r"\b(?:scholarship|award|discount)\b", q)
        and not re.search(r"\bpre[- ]scholarship\b|\bbefore\s+scholarships?\b", q)
    )
    if discount_requested:
        if not re.search(r"\b(?:if|hypothetical|assuming|were\s+awarded|receive|receiving)\b", q):
            return fallback("insufficient_evidence")
        benefit_matches = []
        for item in evidence:
            for match in re.finditer(r"(\d+(?:\.\d+)?)\s*%\s+of\s+tuition", item.chunk.chunk_text, re.I):
                benefit_matches.append((Decimal(match.group(1)), item.evidence_id, item.chunk.chunk_text))
        award_names = re.findall(r"\b(?:Lakbay|Access\s+Support|Community\s+Service)\b", question, re.I)
        if award_names:
            award = award_names[0].casefold().replace(" ", "")
            benefit_matches = [match for match in benefit_matches
                               if award in match[2].casefold().replace(" ", "")]
        distinct = {match[0] for match in benefit_matches}
        if len(distinct) != 1 or any(value <= 0 or value > 100 for value in distinct):
            return fallback("insufficient_evidence")
        percentage = next(iter(distinct))
        if tuition is None or not charges:
            return fallback("insufficient_evidence")
        benefit_ids = {match[1] for match in benefit_matches}
        discount = (tuition * percentage / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        discounted = tuition - discount
        total = discounted + charges[1]
        evidence_ids.update(charges[2])
        evidence_ids.update(benefit_ids)
        award_label = award_names[0] if award_names else "scholarship"
        text = (f"If the fictional {award_label} tuition award were granted, the estimated assessment "
                f"for {units} units would be {_format_money(total)}: tuition {_format_money(tuition)}, "
                f"less a {percentage}% tuition discount ({_format_money(discount)}), plus "
                f"{_format_money(charges[1])} fixed charges. This is conditional, not award approval.")
        return _render_answer([text], _citation_list(evidence, evidence_ids))

    if asks_installments:
        schedule_ids = set()
        percentages = []
        date_matches = []
        for item in evidence:
            for match in re.finditer(
                    r"(\d+(?:\.\d+)?)\s*%\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:,\s*(\d{4}))?",
                    item.chunk.chunk_text, re.I):
                percentages.append(Decimal(match.group(1)))
                date_matches.append((match.group(1), match.group(2), match.group(3), match.group(4)))
                schedule_ids.add(item.evidence_id)
        if len(percentages) != 3 or sum(percentages) != Decimal("100"):
            return fallback("insufficient_evidence")
        balance_matches = [Decimal(value.replace(",", "")) for match in
                           re.findall(r"(?:balance|assessment)\s*(?:of|:)?\s*₱\s*([\d,]+)|₱\s*([\d,]+)\s+(?:verified\s+)?(?:balance|assessment)", question, re.I)
                           for value in match if value]
        if not balance_matches:
            for item in evidence:
                balance_matches.extend(Decimal(value.replace(",", "")) for match in
                    re.findall(r"(?:balance|assessment)\s*:\s*₱\s*([\d,]+)|₱\s*([\d,]+)\s+(?:verified\s+)?balance", item.chunk.chunk_text, re.I)
                    for value in match if value)
        if not balance_matches and units is not None and rate is not None:
            calculation_charges = _fixed_charge_data(evidence)
            if calculation_charges is not None:
                balance_matches = [rate[0] * units + calculation_charges[1]]
                evidence_ids.update(calculation_charges[2])
        if len(set(balance_matches)) != 1:
            return fallback("insufficient_evidence")
        balance = balance_matches[0]
        if balance <= 0 or balance > Decimal("1000000000"):
            return fallback("insufficient_evidence")
        amounts = [(balance * percentage / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                   for percentage in percentages]
        text = "The fictional payment plan yields " + ", ".join(
            f"{percentage}% ({_format_money(amount)})" for percentage, amount in zip(percentages, amounts)
        ) + f" on a {_format_money(balance)} assessment."
        if re.search(r"\b(?:when|date|due)\b", q):
            if len(date_matches) != 3:
                return fallback("insufficient_evidence")
            text += " Scheduled dates are " + ", ".join(
                f"{month} {day}{', ' + year if year else ''}" for _, month, day, year in date_matches
            ) + "."
        return _render_answer([text], _citation_list(evidence, schedule_ids))

    if tuition is None:
        return fallback("insufficient_evidence")
    if charges_requested:
        if charges is None:
            return fallback("insufficient_evidence")
        total = tuition + charges[1]
        evidence_ids.update(charges[2])
        text = (f"The fictional assessment for {units} units is {_format_money(total)}: "
                f"tuition {_format_money(tuition)} plus {_format_money(charges[1])} fixed charges.")
    else:
        text = f"Fictional tuition for {units} units is {_format_money(tuition)}, excluding fixed charges."
    return _render_answer([text], _citation_list(evidence, evidence_ids))


def validate_selection(raw: str, evidence: tuple[Evidence, ...], question: str) -> AnswerResponse:
    """Validate answer-part coverage, quote IDs, high-risk values, and lexical grounding."""
    if not isinstance(raw, str) or len(raw) > 20000:
        raise ValueError("invalid_model_output")
    selection = ModelSelection.model_validate(json.loads(raw, object_pairs_hook=_unique_json_object))
    if not selection.parts:
        # Explicit whole-question abstention, including part-budget overflow.
        if selection.status != "insufficient_evidence":
            raise ValueError("invalid_model_output")
        return fallback("insufficient_evidence")
    by_id = {item.evidence_id: item.chunk for item in evidence}
    if len(by_id) != len(evidence):
        raise ValueError("invalid_evidence")
    question_parts = _answer_question_parts(question)
    if not question_parts or len(selection.parts) != len(question_parts):
        return fallback("insufficient_evidence")
    answers, cited_ids = [], set()
    unsupported = False
    for index, item in enumerate(selection.parts, 1):
        if item.part_index != index or item.part_text.strip() != question_parts[index - 1]:
            raise ValueError("invalid_model_output")
        if item.support == "unsupported":
            if item.answer_text is not None or item.evidence:
                raise ValueError("invalid_model_output")
            unsupported = True
            continue
        if not item.answer_text or not item.answer_text.strip() or not item.evidence:
            raise ValueError("invalid_model_output")
        quotes = []
        for supporting in item.evidence:
            chunk = by_id.get(supporting.evidence_id)
            if chunk is None or not supporting.quote.strip() or supporting.quote not in chunk.chunk_text or not chunk.version:
                raise ValueError("invalid_model_output")
            quotes.append(supporting.quote)
            cited_ids.add(supporting.evidence_id)
        _validate_answer_text(item.answer_text, item.part_text, quotes)
        answers.append(item.answer_text.strip())
    if unsupported or selection.status != "answered":
        return fallback("insufficient_evidence")
    return _render_answer(answers, _citation_list(evidence, cited_ids))


def _selection_failure_reason(error: Exception) -> str:
    """Return only fixed failure labels; never include model output or exception text."""
    if isinstance(error, json.JSONDecodeError):
        return "malformed_json"
    if isinstance(error, ValidationError):
        return "schema_invalid"
    return "validation_failed"


class AnswerService:
    def __init__(self, retriever: Retriever, generator: AnswerGenerator, *, readiness_check=None):
        self.retriever = retriever
        self.generator = generator
        self.readiness_check = readiness_check

    def ask(self, question: str, *, reference_date: date) -> AnswerResponse:
        with diagnostic_request():
            return self._ask(question, reference_date=reference_date)

    def _ask(self, question: str, *, reference_date: date) -> AnswerResponse:
        question = validate_question(question)
        words = set(re.findall(r"\w+", question.casefold()))
        # Conservative demo scope signals, not authentication or an exhaustive
        # classifier. Source access is enforced separately by the retriever.
        if words & {"staff", "private", "password", "passwords", "secret", "secrets"}:
            return fallback("denied")
        if words & {"historical", "superseded", "previous", "older"}:
            return fallback("insufficient_evidence")
        if re.search(r"\b(?:real|official)\s+(?:university|campus|policy|policies|tuition|enrollment|requirements?)\b|"
                     r"\bactual\s+(?:university|campus)\b", question, re.IGNORECASE):
            return fallback("insufficient_evidence")
        if not _answer_question_parts(question):
            return fallback("insufficient_evidence")
        failure_category = "retrieval_failed"
        try:
            if self.readiness_check is not None:
                self.readiness_check()
            evidence = self.retriever.retrieve(question, reference_date=reference_date)
            if not evidence:
                return fallback("insufficient_evidence")
            # Fail safely before paying for generation; preserve whole passages.
            failure_category = "evidence_invalid"
            try:
                validate_evidence_budget(evidence)
            except ValueError as error:
                # Match only our fixed local code; never log the exception itself.
                if error.args == ("evidence_budget_exceeded",):
                    failure_category = "evidence_budget_exceeded"
                raise
            failure_category = "selection_invalid"
            answer = deterministic_financial_answer(question, evidence)
            if answer is None:
                failure_category = "provider_failed"
                raw = self.generator.generate(question, evidence)
                failure_category = "selection_invalid"
                try:
                    answer = validate_selection(raw, evidence, question)
                except IncompleteAnswer:
                    raise
                except Exception as error:
                    diagnostic_event("selection_invalid", selection_reason=_selection_failure_reason(error))
                    return fallback("unavailable")
            if answer.status == "answered":
                # Fail closed if sources, permissions, or passage data changed
                # during generation. This does not eliminate every race window.
                failure_category = "retrieval_failed"
                fresh = self.retriever.retrieve(question, reference_date=reference_date)
                if fresh != evidence:
                    diagnostic_event("evidence_changed")
                    return fallback("unavailable")
            return answer
        except IncompleteAnswer:
            diagnostic_event("selection_invalid", selection_reason="incomplete_answer")
            return fallback("insufficient_evidence")
        except DiagnosticFailure as error:
            diagnostic_event(error.category, error.http_status,
                             provider_code=error.provider_code, provider_param=error.provider_param,
                             provider_classification=error.provider_classification,
                             provider_attribute_states=error.provider_attribute_states,
                             provider_response=error.provider_response,
                             selection_reason=error.selection_reason)
            return fallback("unavailable")
        except Exception:
            # Deliberate application boundary: no provider/database error text,
            # raw model draft, source titles, or stack trace in student responses.
            diagnostic_event(failure_category)
            return fallback("unavailable")
