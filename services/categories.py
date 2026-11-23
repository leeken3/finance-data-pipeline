"""Transaction categorization using merchant rules and local Ollama."""

import json
import re
from urllib.request import Request, urlopen

from config.merchant_rules import MERCHANT_RULES
from config.settings import CATEGORIES, OLLAMA_MODEL, OLLAMA_URL


def normalize_description(value: str) -> str:
    """
    Normalize a transaction description by lowercasing and removing non-alphanumeric characters.

    :param value: The transaction description to normalize.
    :return: The normalized transaction description.
    """
    return " ".join(
        value.lower().replace("&", " and ").replace("-", " ").replace("_", " ").split()
    )


def merchant_rule_matches(words: str, marker: str) -> bool:
    """
    Match multi-word and branded names without false positives from short words.

    :param words: The normalized transaction description.
    :param marker: The merchant name to match.
    :return: True if the merchant name is found, False otherwise.
    """
    marker = normalize_description(marker)
    if len(marker) <= 3:
        return (
            re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", words)
            is not None
        )
    return marker in words


def category_for(description: str) -> str:
    """
    Determine the category for a given transaction description based on merchant rules.

    :param description: The transaction description.
    :return: The category for the transaction.
    """
    words = normalize_description(description)
    return next(
        (
            category
            for category, markers in MERCHANT_RULES.items()
            if any(merchant_rule_matches(words, marker) for marker in markers)
        ),
        "Other",
    )


def categorize_descriptions(
    descriptions, user_id=None, db_factory=None, urlopen_func=urlopen
):
    """
    Combine prior corrections and merchant rules before asking Ollama for unknown merchants.

    :param descriptions: A list of transaction descriptions to categorize.
    :param user_id: The ID of the user for whom to categorize transactions (optional).
    :param db_factory: A callable that returns a database connection (optional).
    :param urlopen_func: A function to open URLs, defaulting to urllib.request.urlopen.
    :return: A list of categories corresponding to the input descriptions.
    """
    fallback = [category_for(description) for description in descriptions]
    if not descriptions:
        return []
    if user_id and db_factory:
        with db_factory() as con:
            prior = con.execute(
                "SELECT description, category FROM transactions WHERE user_id=?",
                (user_id,),
            ).fetchall()
        learned = {
            normalize_description(row["description"]): row["category"]
            for row in prior
            if row["category"] in CATEGORIES
        }
        fallback = [
            learned.get(normalize_description(description), category)
            for description, category in zip(descriptions, fallback)
        ]
    unknown = [index for index, category in enumerate(fallback) if category == "Other"]
    if not unknown:
        return fallback
    prompt = (
        "Categorize each merchant into exactly one of these categories: "
        f"{', '.join(CATEGORIES)}. Use Restaurants for cafes, bakeries, coffee shops, tea shops, bubble tea and food outlets. "
        "Use Bills for cable, internet, phone, telecom, utility, insurance and recurring membership charges. "
        "Prefer a specific category whenever merchant name gives a clear clue, and return ONLY a JSON array of category names in the same order. "
        f"Merchants: {json.dumps([descriptions[index] for index in unknown])}"
    )
    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode()
    try:
        request = Request(
            OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
        )
        with urlopen_func(request, timeout=20) as response:
            answer = json.loads(response.read().decode())["response"].strip()
        if answer.startswith("```"):
            answer = answer.split("```", 2)[1]
            if answer.startswith("json"):
                answer = answer[4:].strip()
        start, end = answer.find("["), answer.rfind("]")
        proposed = (
            json.loads(answer[start : end + 1]) if start >= 0 and end >= start else []
        )
        if not isinstance(proposed, list) or len(proposed) != len(unknown):
            return fallback
        for position, index in enumerate(unknown):
            if proposed[position] in CATEGORIES:
                fallback[index] = proposed[position]
        return fallback
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return fallback
