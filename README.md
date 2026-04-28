# AI CV Screening and Job Matching System

## Overview
This project is an AI-powered CV screening system that evaluates how well a candidate’s CV matches a job description using both keyword-based and semantic similarity techniques.

It combines traditional requirement matching with advanced NLP models to provide a more intelligent and realistic job-fit score.

---

## Features
- CV parsing from PDF
- Skill extraction from CV and job description
- Requirement-based matching
- Semantic similarity using transformer models
- Final hybrid scoring system
- Streamlit web interface
- Visual score breakdown (graphs)
- Matched and missing requirement analysis

---

## Tech Stack
- Python
- Streamlit
- Scikit-learn
- Sentence Transformers (BERT-based models)
- PDFPlumber
- Matplotlib

---

## How It Works
1. Upload a CV (PDF)
2. Paste a job description
3. System extracts skills and requirements
4. Computes:
   - Requirement Match Score
   - Semantic Similarity Score
   - Final Hybrid Score
5. Displays:
   - Score breakdown graph
   - Matched skills
   - Missing skills
   - AI-based recommendation

---

## Installation
```bash
git clone https://github.com/Kushs22/AI-CV-Screening-System.git
cd AI-CV-Screening-System
pip install -r requirements.txt
streamlit run app/streamlit_app.py
