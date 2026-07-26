import hashlib
import re


def normalize_text(text):
    """
    Normalize text so that minor formatting differences
    don't produce different hashes.

    Example:
        " Water  " == "water"
        "Sodium   chloride" == "sodium chloride"
    """

    if text is None:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove leading/trailing spaces
    text = text.strip()

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    return text


def generate_question_hash(
    topic,
    question_text,
    option_a,
    option_b,
    option_c,
    option_d,
    correct_answer,
    subject="Chemistry",
):
    """
    Generate a SHA-256 hash for a question.

    The hash is based on the actual content of the question,
    not its database ID.
    """

    data = "||".join([
        normalize_text(subject),
        normalize_text(topic),
        normalize_text(question_text),
        normalize_text(option_a),
        normalize_text(option_b),
        normalize_text(option_c),
        normalize_text(option_d),
        normalize_text(correct_answer),
    ])

    return hashlib.sha256(data.encode("utf-8")).hexdigest()