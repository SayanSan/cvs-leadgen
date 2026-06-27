"""
LLM brain for CVS agents — powered by NVIDIA NIM (Llama 3.3 70B).
OpenAI-compatible API, falls back to rule-based if NIM key is missing.
"""

import logging
from typing import Optional
from openai import OpenAI
from config import config

logger = logging.getLogger(__name__)

_client = None

def _get_client() -> Optional[OpenAI]:
    global _client
    if not config.NIM_API_KEY:
        return None
    if _client is None:
        _client = OpenAI(
            base_url=config.NIM_BASE_URL,
            api_key=config.NIM_API_KEY,
        )
    return _client


def chat(system: str, user: str, temperature: float = 0.7, max_tokens: int = 512) -> Optional[str]:
    """
    Send a chat request to NVIDIA NIM.
    Returns the response text, or None if NIM is unavailable.
    """
    client = _get_client()
    if not client:
        logger.debug("NIM not configured — skipping LLM call")
        return None
    try:
        resp = client.chat.completions.create(
            model=config.NIM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"NIM call failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Outreach helpers
# ---------------------------------------------------------------------------

def personalize_email_opener(lead: dict) -> Optional[str]:
    """
    Generate a personalized 2-3 sentence email opener for this lead using LLM.
    Returns None if NIM unavailable (caller uses rule-based fallback).
    """
    system = (
        "You are an expert cold email copywriter for Code Visionary Services, "
        "a company that builds websites, mobile apps, and runs digital marketing for businesses in India. "
        "Write a short, natural 2-3 sentence opener for a cold email to a potential client. "
        "Sound human, not salesy. No subject line. No sign-off. Just the opener paragraph."
    )
    user = (
        f"Business name: {lead.get('company', '')}\n"
        f"Industry/Type: {lead.get('industry', '')}\n"
        f"Location: {lead.get('location', '')}\n"
        f"Contact title: {lead.get('title', 'Business Owner')}\n"
        f"Service they likely need: {lead.get('service_needed', 'website')}\n\n"
        "Write a personalized opener that references their specific business type and location, "
        "and hints at the problem we solve (online presence / getting more customers digitally). "
        "Keep it under 60 words."
    )
    return chat(system, user, temperature=0.8, max_tokens=120)


def personalize_pain_point(lead: dict) -> Optional[str]:
    """
    Generate a one-line pain point specific to this lead.
    Returns None if NIM unavailable.
    """
    system = (
        "You write concise, specific pain points for cold emails targeting Indian businesses. "
        "Output a single phrase (5-12 words) describing the main digital challenge this business faces. "
        "No full sentences, no punctuation at end."
    )
    user = (
        f"Business: {lead.get('company', '')}, "
        f"Industry: {lead.get('industry', '')}, "
        f"Location: {lead.get('location', '')}, "
        f"Service needed: {lead.get('service_needed', 'website')}"
    )
    return chat(system, user, temperature=0.6, max_tokens=30)


# ---------------------------------------------------------------------------
# Sales / reply helpers
# ---------------------------------------------------------------------------

def classify_reply(reply_text: str, lead: dict) -> Optional[dict]:
    """
    Use LLM to classify a reply and draft a response.
    Returns {"intent": str, "draft": str} or None if NIM unavailable.
    Intent: interested | not_interested | question | unsubscribe | auto_reply
    """
    system = (
        "You are a sales assistant for Code Visionary Services (websites, apps, digital marketing). "
        "Classify the email reply intent and draft a short response. "
        'Respond in JSON with exactly two keys: "intent" and "draft". '
        'Intent must be one of: interested, not_interested, question, unsubscribe, auto_reply. '
        "Draft should be 2-4 sentences max, warm and professional. "
        f"Always include the Calendly link if intent is interested or question: {config.CALENDLY_MEETING_LINK}"
    )
    user = (
        f"Lead company: {lead.get('company', '')}\n"
        f"Lead name: {lead.get('name', '')}\n"
        f"Their reply:\n\"\"\"\n{reply_text}\n\"\"\""
    )
    raw = chat(system, user, temperature=0.3, max_tokens=200)
    if not raw:
        return None
    try:
        import json, re
        # Extract JSON even if wrapped in markdown
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        logger.warning(f"Failed to parse LLM reply classification: {e} — raw: {raw[:100]}")
    return None


def draft_followup(lead: dict, follow_up_count: int) -> Optional[str]:
    """
    Generate a fresh follow-up paragraph for this lead.
    Returns None if NIM unavailable.
    """
    system = (
        "You write short, friendly follow-up cold email paragraphs for Code Visionary Services. "
        "Each follow-up should take a different angle than the last. "
        "2-3 sentences max. No greetings, no sign-off."
    )
    user = (
        f"Business: {lead.get('company', '')}, "
        f"Industry: {lead.get('industry', '')}, "
        f"Service needed: {lead.get('service_needed', 'website')}, "
        f"Follow-up number: {follow_up_count + 1}. "
        "Write a new angle — maybe mention a specific result, a local competitor doing well online, "
        "or a simple question to spark a reply."
    )
    return chat(system, user, temperature=0.8, max_tokens=100)
