#  AI CV Screening and Job Matching System

 Built with Python, NLP, and Machine Learning

---

##  Overview

This project is an AI-powered CV screening system that evaluates how well a candidate’s CV matches a job description using both **keyword-based matching** and **semantic similarity techniques**.

It helps identify:
- ✅ Matched skills
- ❌ Missing skills
- 📊 Overall CV-job fit score

---

## ⚙️ Key Features

- Extracts text from PDF CVs
- Performs keyword-based requirement matching
- Uses semantic similarity (Sentence Transformers)
- Generates hybrid CV-job match score
- Provides matched and missing skills
- Interactive Streamlit web interface
- Visual score breakdown using graphs

---

## 🧠 Tech Stack

- Python
- Streamlit
- Scikit-learn
- Sentence Transformers
- PyTorch
- PDFPlumber
- Matplotlib

---

## 📊 Demo

![App Screenshot](images/demo.png)

---

## 📈 How It Works

1. Upload a CV (PDF format)
2. Paste a job description
3. System extracts and processes text
4. Computes:
   - Requirement Match Score
   - Semantic Similarity Score
   - Final Hybrid Score
5. Displays:
   - Graphical score breakdown
   - Matched requirements
   - Missing requirements
   - AI-based recommendation

---

## 🚀 How to Run

```bash
git clone https://github.com/Kushs22/AI-CV-Screening-System.git
cd AI-CV-Screening-System
pip install -r requirements.txt
streamlit run app/streamlit_app.py

AI-CV-Screening-System/
│
├── app/
│   └── streamlit_app.py
│
├── src/
│   ├── resume_parser.py
│   ├── skill_extractor.py
│   ├── semantic_matcher.py
│   └── final_matcher.py
│
├── data/
│   ├── resumes/
│   └── job_descriptions/
│
├── images/
│   └── demo.png
│
├── requirements.txt
├── README.md
└── .gitignore
