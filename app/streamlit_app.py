import os
import sys
import tempfile
import streamlit as st
import matplotlib.pyplot as plt

# Fix import path
sys.path.append(os.path.abspath("src"))

from resume_parser import extract_text_from_pdf
from skill_extractor import extract_key_phrases
from semantic_matcher import calculate_semantic_similarity
from final_matcher import (
    calculate_final_score,
    generate_recommendation,
    generate_explanation
)

# Page config
st.set_page_config(page_title="AI CV Screening", layout="wide")

# Title
st.title("📄 AI CV Screening and Job Matching System")

st.write(
    "Upload a CV and paste any job description to generate a hybrid CV-job match score "
    "using requirement matching and semantic similarity."
)

# Upload CV
uploaded_file = st.file_uploader("Upload CV PDF", type=["pdf"])

# Job Description
job_description = st.text_area(
    "Paste Job Description",
    height=250,
    placeholder="Paste any job description here..."
)

# Analyse Button
if st.button("Analyse CV"):

    if uploaded_file is not None and job_description.strip() != "":

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            temp_path = tmp_file.name

        # Extract CV text
        cv_text = extract_text_from_pdf(temp_path)

        # Extract phrases from CV and job description
        cv_skills = extract_key_phrases(cv_text)
        jd_skills = extract_key_phrases(job_description)

        # Requirement matching
        matched = list(set(cv_skills) & set(jd_skills))
        missing = list(set(jd_skills) - set(cv_skills))

        # Requirement score
        if len(jd_skills) > 0:
            requirement_score = round((len(matched) / len(jd_skills)) * 100, 2)
        else:
            requirement_score = 0

        # Semantic score
        semantic_score = round(
            calculate_semantic_similarity(cv_text, job_description),
            2
        )

        # Final score
        final_score = calculate_final_score(requirement_score, semantic_score)

        # Recommendation and explanation
        recommendation = generate_recommendation(final_score)
        explanation = generate_explanation(matched, missing)

        # =========================
        # Results Section
        # =========================

        st.subheader("📊 Final Result")

        col1, col2, col3 = st.columns(3)

        col1.metric("Requirement Score", f"{requirement_score}%")
        col2.metric("Semantic Score", f"{semantic_score}%")
        col3.metric("Final Score", f"{final_score}%")

        st.success(recommendation)

        # =========================
        # Score Graph
        # =========================

        st.subheader("📈 Score Breakdown")

        scores = {
            "Requirement Score": requirement_score,
            "Semantic Score": semantic_score,
            "Final Score": final_score
        }

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(scores.keys(), scores.values())
        ax.set_ylim(0, 100)
        ax.set_ylabel("Score (%)")
        ax.set_title("CV-Job Matching Score Breakdown")

        for index, value in enumerate(scores.values()):
            ax.text(index, value + 2, f"{value}%", ha="center")

        st.pyplot(fig)

        # =========================
        # Explanation
        # =========================

        st.subheader("🧠 AI Insight")
        st.write(explanation)

        # =========================
        # Matched Requirements
        # =========================

        st.subheader("✅ Key Matching Skills")
        if matched:
            for skill in matched[:8]:
                st.write(f"• {skill}")
        else:
            st.write("No strong matches found.")

        # =========================
        # Missing Requirements
        # =========================

        st.subheader("⚠️ Important Missing Skills")
        clean_missing = [m for m in missing if len(m.split()) > 1][:8]

        if clean_missing:
            for skill in clean_missing:
                st.write(f"• {skill}")
        else:
            st.write("No major gaps detected.")

        # =========================
        # Suggestions
        # =========================

        st.subheader("💡 CV Improvement Suggestions")
        if clean_missing:
            st.write("To improve alignment, consider adding stronger evidence of:")
            for item in clean_missing[:5]:
                st.write(f"• {item}")
        else:
            st.write("Your CV is well aligned with this job description.")

        # =========================
        # Safety Notice
        # =========================

        st.subheader("⚠️ Safety Notice")
        st.info(
            "This system is designed as a decision-support tool only. "
            "It should not be used as the sole basis for hiring decisions."
        )

    else:
        st.warning("Please upload a CV and paste a job description.")