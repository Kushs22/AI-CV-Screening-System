"""
====================================================
AI CV Screening System - Semantic Matcher
====================================================

Purpose:
This module compares CVs with job descriptions using semantic similarity.
Unlike keyword matching, semantic matching compares meaning, so it can work
across different job domains.
"""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from resume_parser import load_all_resumes
from skill_extractor import load_job_description


# Load a pre-trained sentence embedding model
# This converts text into numerical vectors that capture meaning.
model = SentenceTransformer("all-MiniLM-L6-v2")


def calculate_semantic_similarity(cv_text, job_description):
    """
    Calculates semantic similarity between a CV and a job description.

    Parameters:
        cv_text (str): Extracted CV text.
        job_description (str): Job description text.

    Returns:
        float: Similarity score as a percentage.
    """

    # Convert CV text and job description into embeddings
    cv_embedding = model.encode([cv_text])
    job_embedding = model.encode([job_description])

    # Calculate cosine similarity between both embeddings
    similarity = cosine_similarity(cv_embedding, job_embedding)[0][0]

    # Convert similarity to percentage
    return round(similarity * 100, 2)


def classify_match(score):
    """
    Classifies match strength based on semantic similarity score.
    """

    if score >= 75:
        return "Strong Match"
    elif score >= 55:
        return "Moderate Match"
    elif score >= 35:
        return "Weak Match"
    else:
        return "Low Match"


if __name__ == "__main__":

    resumes_folder = "data/resumes"
    job_description_path = "data/job_descriptions/job_description.txt"

    # Load all CVs
    resumes = load_all_resumes(resumes_folder)

    # Load job description
    job_description = load_job_description(job_description_path)

    print("\n===== SEMANTIC CV-JOB MATCHING =====\n")

    for file_name, cv_text in resumes.items():

        score = calculate_semantic_similarity(cv_text, job_description)
        match_label = classify_match(score)

        print("------------------------------------")
        print(f"CV File: {file_name}")
        print(f"Semantic Match Score: {score}%")
        print(f"Match Category: {match_label}")