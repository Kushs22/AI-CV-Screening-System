"""
Final Hybrid Matcher for AI CV Screening System.
Combines requirement matching, semantic similarity, recommendation,
and explanation generation.
"""

from resume_parser import load_all_resumes
from skill_extractor import (
    load_job_description,
    extract_key_phrases,
    compare_cv_to_job
)
from semantic_matcher import calculate_semantic_similarity


def calculate_final_score(requirement_score, semantic_score):
    """
    Weighted final score.
    Semantic similarity gets higher weight because it captures meaning.
    """

    final_score = (0.4 * requirement_score) + (0.6 * semantic_score)
    return round(final_score, 2)


def generate_recommendation(final_score):
    """
    Generate recommendation based on final score.
    """

    if final_score >= 75:
        return "Strong Fit - Candidate closely matches the job requirements."
    elif final_score >= 55:
        return "Moderate Fit - Candidate has relevant experience but some gaps exist."
    elif final_score >= 35:
        return "Partial Fit - Candidate shows some alignment but important gaps remain."
    else:
        return "Low Fit - Candidate does not strongly match this specific job description."


def generate_explanation(matched_requirements, missing_requirements):
    """
    Generate a short explanation for the screening decision.
    """

    explanation = []

    if len(matched_requirements) >= len(missing_requirements):
        explanation.append(
            "The CV shows strong alignment with several job requirements."
        )
    else:
        explanation.append(
            "The CV shows some alignment, but several important requirements are missing."
        )

    if matched_requirements:
        explanation.append(
            "Key matched areas include: "
            + ", ".join(matched_requirements[:5])
            + "."
        )

    if missing_requirements:
        explanation.append(
            "Key gaps include: "
            + ", ".join(missing_requirements[:5])
            + "."
        )

    return " ".join(explanation)


if __name__ == "__main__":

    resumes_folder = "data/resumes"
    job_description_path = "data/job_descriptions/job_description.txt"

    resumes = load_all_resumes(resumes_folder)
    job_description = load_job_description(job_description_path)

    job_requirements = extract_key_phrases(job_description)

    print("\n===== FINAL HYBRID CV-JOB MATCHING SYSTEM =====\n")

    for file_name, cv_text in resumes.items():

        cv_phrases = extract_key_phrases(cv_text)

        matched, missing, requirement_score = compare_cv_to_job(
            cv_phrases,
            job_requirements
        )

        semantic_score = calculate_semantic_similarity(
            cv_text,
            job_description
        )

        final_score = calculate_final_score(
            requirement_score,
            semantic_score
        )

        recommendation = generate_recommendation(final_score)
        explanation = generate_explanation(matched, missing)

        print("----------------------------------------")
        print(f"CV File: {file_name}")
        print(f"Requirement Match Score: {requirement_score}%")
        print(f"Semantic Match Score: {semantic_score}%")
        print(f"Final Hybrid Match Score: {final_score}%")
        print(f"Recommendation: {recommendation}")
        print(f"Explanation: {explanation}")
        print(f"Matched Requirements: {matched[:10]}")
        print(f"Missing Requirements: {missing[:10]}")