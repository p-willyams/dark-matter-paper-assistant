import re

SCOPE_DESCRIPTION = (
    "dark matter in astrophysics and particle physics — including basic "
    "concepts and definitions, observational evidence, particle candidates "
    "such as WIMPs, cold vs. warm dark matter, experimental detection, and "
    "general reviews on the subject"
)

CLASSIFIER_PROMPT = f"""
You are a classifier for a question-answering system. The system's scope is:
{SCOPE_DESCRIPTION}.

Classify the user's question into exactly one category. Respond with ONLY
one word, no explanation:
- IN_SCOPE — the question relates to the topic above in any way, including
  basic definitions, general concepts, or introductory questions about it
- OUT_OF_SCOPE — the question has no relation to the topic at all

When in doubt, classify as IN_SCOPE.

Examples:
Question: What is dark matter?
Answer: IN_SCOPE

Question: How do WIMPs differ from axions?
Answer: IN_SCOPE

Question: What's the capital of France?
Answer: OUT_OF_SCOPE

Question: Can you write me a poem about love?
Answer: OUT_OF_SCOPE

Question: What evidence supports the existence of dark matter?
Answer: IN_SCOPE

Now classify this question:
Question: {{question}}
Answer:
"""


def is_question_in_scope(query, client_openai, model):
    response = client_openai.responses.create(
        model=model,
        instructions=CLASSIFIER_PROMPT.format(question=query),
        input=query,
        max_output_tokens=200,
        reasoning={"effort": "low"},
    )
    classification = response.output_text.strip().upper()

    is_in_scope = "IN_SCOPE" in classification
    is_out_of_scope = "OUT_OF_SCOPE" in classification

    if is_in_scope and not is_out_of_scope:
        return True
    if is_out_of_scope and not is_in_scope:
        return False
    retry_prompt = (
        f"Topic: {SCOPE_DESCRIPTION}.\n"
        f'Question: "{query}"\n'
        "Is this question about the topic above? Answer with exactly one "
        "word: YES or NO."
    )
    retry_response = client_openai.responses.create(
        model=model,
        instructions=retry_prompt,
        input=query,
        max_output_tokens=50,
        reasoning={"effort": "low"},
    )
    retry_text = retry_response.output_text.strip().upper()

    if "YES" in retry_text and "NO" not in retry_text:
        return True
    if "NO" in retry_text and "YES" not in retry_text:
        return False

    return False


CITATION_PATTERN = re.compile(r"\(([^()]*?,\s*[^()]*?,\s*(19|20)\d{2}[^()]*?)\)")


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
