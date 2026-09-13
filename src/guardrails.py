import re

SCOPE_DESCRIPTION = (
    "scientific articles about dark matter (observational evidence, "
    "particle candidates such as WIMPs, cold vs. warm dark matter, "
    "experimental detection, and general reviews on the subject)"
)

CLASSIFIER_PROMPT = f"""
You are a classifier. The scope of this system is: {SCOPE_DESCRIPTION}.

Classify the user's question into one of two categories, responding
ONLY with a single word, no explanation:
- DENTRO_DO_ESCOPO — if the question is about the theme above, even indirectly
- FORA_DO_ESCOPO — if the question is unrelated to the theme

Question: {{question}}
"""

CITATION_PATTERN = re.compile(r"\(([^()]*?,\s*[^()]*?,\s*(19|20)\d{2}[^()]*?)\)")


def is_question_in_scope(query, client_openai, model):
    response = client_openai.responses.create(
        model=model,
        instructions=CLASSIFIER_PROMPT.format(question=query),
        input=query,
        max_output_tokens=10,
    )
    classification = response.output_text.strip().upper()
    return "DENTRO" in classification


def extract_citations(answer_text):
    return [m.group(1) for m in CITATION_PATTERN.finditer(answer_text)]


def check_citations(answer_text, valid_titles):
    citations = extract_citations(answer_text)
    suspicious = []

    for citation in citations:
        cited_title = citation.split(",")[0].strip().lower()
        matches_any = any(
            cited_title in valid_title.lower() or valid_title.lower() in cited_title
            for valid_title in valid_titles
            if valid_title
        )
        if not matches_any:
            suspicious.append(citation)

    return suspicious
