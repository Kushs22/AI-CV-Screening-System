"""
====================================================
AI CV Screening System - General Requirement Extractor
====================================================

Purpose:
This module extracts meaningful requirements from any job description
and compares them with any CV.

It avoids fixed AI/ML-only skill lists and reduces noisy generic phrases.
"""

import re
from sklearn.feature_extraction.text import CountVectorizer
from resume_parser import load_all_resumes


CUSTOM_STOPWORDS = {
    "ai", "ml", "job", "role", "work", "working", "candidate",
    "experience", "skills", "skill", "team", "teams", "good",
    "strong", "ability", "able", "knowledge", "understanding",
    "responsible", "requirements", "required", "ideal",
    "technology", "technologies", "system", "systems",
    "model", "models", "code", "open", "source",
    "software", "development", "real", "world", "new"
}


BAD_WORDS = {
    "play", "push", "work", "working", "good", "strong",
    "new", "real", "critical", "able", "role", "provide",
    "closely", "wants", "loves", "current", "actively",
    "engage", "broader", "differentiate"
}


def clean_text(text):
    """
    Clean raw text by lowercasing, removing symbols, and normalising spaces.
    """

    text = text.lower()
    text = re.sub(r"[^a-zA-Z0-9+#.\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_phrases(phrases):
    """
    Remove noisy, generic, or weak phrases.
    """

    cleaned = []

    for phrase in phrases:
        phrase = phrase.strip().lower()
        words = phrase.split()

        # Keep only 2-word and 3-word phrases
        if len(words) < 2 or len(words) > 3:
            continue

        # Remove phrases containing numbers
        if any(char.isdigit() for char in phrase):
            continue

        # Remove phrases containing generic/noisy words
        if any(word in BAD_WORDS for word in words):
            continue

        # Remove phrases where all words are generic
        if all(word in CUSTOM_STOPWORDS for word in words):
            continue

        # Remove phrases that start or end with weak generic words
        if words[0] in CUSTOM_STOPWORDS or words[-1] in CUSTOM_STOPWORDS:
            continue

        cleaned.append(phrase)

    return sorted(set(cleaned))


def extract_key_phrases(text, top_n=50):
    """
    Extract meaningful 2-word and 3-word phrases from any CV/job description.
    """

    cleaned_text = clean_text(text)

    vectorizer = CountVectorizer(
        stop_words="english",
        ngram_range=(2, 3),
        max_features=top_n
    )

    phrase_matrix = vectorizer.fit_transform([cleaned_text])
    phrases = vectorizer.get_feature_names_out()

    return clean_phrases(phrases)


def compare_cv_to_job(cv_phrases, job_phrases):
    """
    Compare extracted CV phrases against job-description phrases.
    """

    cv_set = set(cv_phrases)
    job_set = set(job_phrases)

    matched_requirements = sorted(cv_set.intersection(job_set))
    missing_requirements = sorted(job_set.difference(cv_set))

    if len(job_set) == 0:
        match_score = 0
    else:
        match_score = (len(matched_requirements) / len(job_set)) * 100

    return matched_requirements, missing_requirements, round(match_score, 2)


def load_job_description(file_path):
    """
    Load job description from a text file.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


if __name__ == "__main__":

    resumes_folder = "data/resumes"
    job_description_path = "data/job_descriptions/job_description.txt"

    resumes = load_all_resumes(resumes_folder)
    job_description = load_job_description(job_description_path)

    job_requirements = extract_key_phrases(job_description)

    print("\n===== EXTRACTED JOB REQUIREMENTS =====")
    print(job_requirements)

    for file_name, cv_text in resumes.items():

        print("\n====================================")
        print(f"Processing CV: {file_name}")
        print("====================================")

        cv_phrases = extract_key_phrases(cv_text)

        matched, missing, score = compare_cv_to_job(
            cv_phrases,
            job_requirements
        )

        print("\nCV Key Phrases Found:")
        print(cv_phrases)

        print("\nMatched Requirements:")
        print(matched)

        print("\nMissing Requirements:")
        print(missing)

        print("\nGeneral Requirement Match Score:")
        print(f"{score}%")