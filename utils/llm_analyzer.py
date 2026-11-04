"""AI-backed contract analysis and chat helpers.

The provider SDK is imported lazily so the web app can still start and render a
useful configuration error when the optional AI dependency is unavailable.
"""

import json
import logging
import os
import re
from typing import Any, Iterator, TYPE_CHECKING

from config import Config


logger = logging.getLogger(__name__)
_client = None
_client_key = None

if TYPE_CHECKING:  # pragma: no cover - only used by static type checkers
    from sarvamai import SarvamAI


class LLMServiceError(RuntimeError):
    """An error that is safe to show to Legal-Ease users."""


_PROVIDER_DETAIL_RE = re.compile(
    r'\b(?:provider|sdk|client library|traceback|stack trace)\b|'
    r'(?:api[_ -]?key|authorization|bearer)\s*[:=]',
    re.IGNORECASE,
)


LANGUAGE_NAMES = {
    'hindi': 'Hindi',
    'tamil': 'Tamil',
    'telugu': 'Telugu',
    'marathi': 'Marathi',
    'bengali': 'Bengali',
    'kannada': 'Kannada',
    'gujarati': 'Gujarati',
}

SARVAM_LANG_CODES = {
    'hindi': 'hi-IN',
    'tamil': 'ta-IN',
    'telugu': 'te-IN',
    'marathi': 'mr-IN',
    'bengali': 'bn-IN',
    'kannada': 'kn-IN',
    'gujarati': 'gu-IN',
}


def _get_client() -> Any:
    global _client, _client_key

    api_key = os.getenv('SARVAM_API_KEY', '').strip()
    if not api_key:
        raise LLMServiceError(
            'The AI service is not configured. Add your API key to the .env file and restart the server.'
        )

    try:
        # Import only when an AI request is made. This keeps the Flask app
        # usable for uploads, history, and configuration troubleshooting even
        # if the SDK is not installed correctly.
        from sarvamai import SarvamAI

        if _client is None or _client_key != api_key:
            _client = SarvamAI(
                api_subscription_key=api_key,
                timeout=float(os.getenv('SARVAM_TIMEOUT_SECONDS', '90')),
            )
            _client_key = api_key
        return _client
    except LLMServiceError:
        raise
    except Exception as exc:
        logger.exception('AI client could not be initialised')
        raise LLMServiceError(
            'The AI service could not be started. Please check the app configuration and try again.'
        ) from exc


def _public_error(exc: Exception) -> str:
    """Turn provider failures into messages that do not expose implementation details."""
    status_code = (
        getattr(exc, 'status_code', None)
        or getattr(exc, 'status', None)
        or getattr(getattr(exc, 'response', None), 'status_code', None)
    )
    try:
        status_code = int(status_code) if status_code is not None else None
    except (TypeError, ValueError):
        status_code = None

    if status_code in {401, 403}:
        return 'The AI service could not authenticate. Please verify your API key and try again.'
    if status_code == 402:
        return 'The AI service has no available credits. Please check your account and try again.'
    if status_code == 429:
        return 'The AI service is busy. Please wait a moment and try again.'
    return 'The AI service is temporarily unavailable. Please try again shortly.'


def safe_error_message(error: Exception | str) -> str:
    """Return only a safe, concise message for a browser response.

    This protects the UI from raw SDK exceptions and from stale provider names
    that may exist in an older database record.
    """
    if isinstance(error, LLMServiceError):
        message = str(error).strip()
        if message.startswith('The AI service') and not _PROVIDER_DETAIL_RE.search(message):
            return message[:240]

    if isinstance(error, Exception):
        return _public_error(error)

    message = str(error).strip()
    if (
        not message
        or not message.startswith('The AI service')
        or _PROVIDER_DETAIL_RE.search(message)
    ):
        return 'The AI service is temporarily unavailable. Please try again shortly.'
    return message[:240]


def _field(value, name: str, default=None):
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _extract_content(response) -> str:
    choices = _field(response, 'choices', []) or []
    if not choices:
        return ''
    message = _field(choices[0], 'message', {})
    content = _field(message, 'content', '')
    return str(content or '').strip()


def _chat(messages: list[dict[str, str]], *, stream: bool = False, max_tokens: int = 800):
    try:
        response = _get_client().chat.completions(
            messages=messages,
            model=Config.SARVAM_MODEL,
            reasoning_effort=Config.SARVAM_REASONING_EFFORT,
            stream=stream,
            max_tokens=max_tokens,
        )
    except LLMServiceError:
        raise
    except Exception as exc:
        logger.exception('AI chat request failed')
        raise LLMServiceError(_public_error(exc)) from exc

    if stream:
        return response

    content = _extract_content(response)
    if not content:
        logger.warning('AI service returned a response without visible content')
        raise LLMServiceError('The AI service did not return an answer. Please try again.')
    return content


def _translate(text: str, target_language: str) -> str:
    """Translate a short English response; keep the English result if translation fails."""
    if not text or not text.strip():
        return text

    target_code = SARVAM_LANG_CODES.get(target_language)
    if not target_code:
        return text

    try:
        client = _get_client()
        parts = _split_for_translation(text)
        translated_parts = []
        for part in parts:
            response = client.text.translate(
                input=part,
                source_language_code='en-IN',
                target_language_code=target_code,
                speaker_gender='Female',
                mode='formal',
            )
            translated = _field(response, 'translated_text', '')
            if not translated:
                return text
            translated_parts.append(str(translated).strip())
        return ' '.join(translated_parts)
    except Exception:
        logger.exception('AI translation failed; returning the English response')
        return text


def _split_for_translation(text: str, max_chars: int = 850) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks, current = [], ''
    for sentence in re.split(r'(?<=[.!?])\s+', text):
        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = f'{current} {sentence}'.strip()
    if current:
        chunks.append(current)
    return chunks


def _analysis_messages(contract_text: str) -> list[dict[str, str]]:
    contract = contract_text[:16000]
    system = (
        'You are Legal-Ease, an expert Indian legal contract analyst. '
        'Help non-lawyers understand the supplied agreement. Return valid JSON only; '
        'do not include markdown, commentary, or reasoning outside the JSON.'
    )
    prompt = f'''Analyze this contract and return this exact JSON shape:
{{
  "summary": "3–5 sentence plain-English summary",
  "overall_risk": "High | Medium | Low",
  "contract_type": "best matching contract type",
  "clauses": [
    {{
      "type": "Liability | Termination | Payment | Auto-Renewal | Data Sharing | Penalty | Indemnification | Arbitration | Non-Compete | General",
      "original": "relevant contract excerpt (max 250 characters)",
      "simplified": "plain-English explanation",
      "severity": "High | Medium | Low",
      "is_red_flag": true,
      "explanation": "practical impact on the signer"
    }}
  ]
}}

Only include clauses supported by the contract. Treat unlimited liability, one-sided termination, automatic renewal, broad data sharing, non-competes, and steep penalties as possible red flags.

CONTRACT TEXT:
{contract}'''
    return [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': prompt},
    ]


def _parse_analysis(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned, flags=re.IGNORECASE)

    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if not match:
        logger.warning('AI analysis response did not contain JSON')
        raise LLMServiceError('The AI service returned an unreadable analysis. Please try again.')

    try:
        result = json.loads(match.group())
    except json.JSONDecodeError as exc:
        logger.warning('AI analysis JSON could not be decoded: %s', exc)
        raise LLMServiceError('The AI service returned an unreadable analysis. Please try again.') from exc

    if not isinstance(result, dict):
        raise LLMServiceError('The AI service returned an unreadable analysis. Please try again.')
    return result


def analyze_contract(contract_text: str, language: str = 'hindi') -> dict:
    result = _parse_analysis(_chat(_analysis_messages(contract_text), max_tokens=2600))

    summary = str(result.get('summary') or 'No summary was returned.')
    risk = str(result.get('overall_risk') or 'Medium').title()
    if risk not in {'High', 'Medium', 'Low'}:
        risk = 'Medium'

    clauses = []
    for clause in result.get('clauses') or []:
        if not isinstance(clause, dict):
            continue
        severity = str(clause.get('severity') or 'Low').title()
        clauses.append({
            'type': str(clause.get('type') or 'General'),
            'original': str(clause.get('original') or '')[:2000],
            'simplified': str(clause.get('simplified') or ''),
            'severity': severity if severity in {'High', 'Medium', 'Low'} else 'Low',
            'is_red_flag': bool(clause.get('is_red_flag', False)),
            'explanation': str(clause.get('explanation') or ''),
        })

    return {
        'summary': summary,
        'translated_summary': _translate(summary, language),
        'overall_risk': risk,
        'contract_type': str(result.get('contract_type') or 'General Contract'),
        'clauses': [
            {**clause, 'translated': _translate(clause['simplified'], language)}
            for clause in clauses
        ],
    }


def _chat_messages(contract_text: str, user_question: str, chat_history: list | None) -> list[dict[str, str]]:
    system = (
        'You are Legal-Ease, a friendly Indian legal assistant. Answer only from the uploaded '
        'contract. Use plain English, keep the answer to 2–4 sentences, explain the practical '
        'effect, and clearly say when the contract does not answer the question. This is '
        'informational support, not legal advice.\n\n'
        f'CONTRACT:\n{contract_text[:12000]}'
    )
    messages = [{'role': 'system', 'content': system}]
    for message in (chat_history or [])[-6:]:
        role = message.get('role') if isinstance(message, dict) else None
        content = message.get('content') if isinstance(message, dict) else None
        if role in {'user', 'assistant'} and isinstance(content, str) and content.strip():
            messages.append({'role': role, 'content': content.strip()})
    messages.append({'role': 'user', 'content': user_question})
    return messages


def chat_about_contract(
    contract_text: str,
    user_question: str,
    language: str = 'hindi',
    chat_history: list | None = None,
) -> str:
    answer = _chat(_chat_messages(contract_text, user_question, chat_history), max_tokens=800)
    translated = _translate(answer, language)
    if translated and translated != answer:
        return f'{answer}\n\n---\n🌐 {LANGUAGE_NAMES.get(language, language.title())}:\n{translated}'
    return answer


def stream_chat_about_contract(
    contract_text: str,
    user_question: str,
    language: str = 'hindi',
    chat_history: list | None = None,
) -> Iterator[str]:
    """Yield only answer content, then the translated answer when available."""
    response_stream = _chat(
        _chat_messages(contract_text, user_question, chat_history),
        stream=True,
        max_tokens=800,
    )
    answer_parts = []
    try:
        for chunk in response_stream:
            choices = _field(chunk, 'choices', []) or []
            if not choices:
                continue
            delta = _field(choices[0], 'delta', {})
            content = _field(delta, 'content', '')
            if content:
                text = str(content)
                answer_parts.append(text)
                yield text
    except Exception as exc:
        logger.exception('AI streamed chat response failed')
        raise LLMServiceError(_public_error(exc)) from exc

    answer = ''.join(answer_parts).strip()
    if not answer:
        raise LLMServiceError('The AI service did not return an answer. Please try again.')

    translated = _translate(answer, language)
    if translated and translated != answer:
        yield f'\n\n---\n🌐 {LANGUAGE_NAMES.get(language, language.title())}:\n{translated}'


def get_clause_comparison(clause_text: str, clause_type: str) -> str:
    prompt = (
        f'Compare this {clause_type} clause against a typical fair Indian contract clause.\n\n'
        f'CLAUSE:\n{clause_text}\n\n'
        'Answer in three concise plain-English points: (1) the main difference, '
        '(2) a fair alternative, and (3) what the signer could negotiate. '
        'Keep the answer under 150 words and avoid claiming legal certainty.'
    )
    return _chat([{'role': 'user', 'content': prompt}], max_tokens=700)
