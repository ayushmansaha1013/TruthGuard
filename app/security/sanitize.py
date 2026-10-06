import re

def sanitize(text):

    text = re.sub(r"<.*?>", "", text)

    text = text.replace("\n", " ")

    text = text.replace("\r", " ")

    text = text.strip()

    dangerous_phrases = [
        "ignore previous instructions",
        "ignore all instructions",
        "system prompt",
        "reveal prompt"
    ]

    for phrase in dangerous_phrases:
        text = text.replace(phrase, "")

    return text[:1000]