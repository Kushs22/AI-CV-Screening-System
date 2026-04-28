"""
====================================================
AI CV Screening System - General Resume Parser
====================================================

Purpose:
This module extracts text from every PDF resume placed inside
the data/resumes folder.

This allows the system to process any CV, not just one fixed CV.
"""

import os
import pdfplumber


def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file.

    Parameters:
        file_path (str): Path to the PDF resume.

    Returns:
        str: Extracted resume text.
    """

    extracted_text = ""

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()

            # Some PDF pages may return None, so we check before adding
            if page_text:
                extracted_text += page_text + "\n"

    return extracted_text


def load_all_resumes(resumes_folder):
    """
    Load and extract text from all PDF resumes in a folder.

    Parameters:
        resumes_folder (str): Folder containing resume PDF files.

    Returns:
        dict: Dictionary where key = file name, value = extracted text.
    """

    resumes_data = {}

    # Loop through every file in the resumes folder
    for file_name in os.listdir(resumes_folder):

        # Only process PDF files
        if file_name.lower().endswith(".pdf"):

            file_path = os.path.join(resumes_folder, file_name)

            print(f"Processing resume: {file_name}")

            extracted_text = extract_text_from_pdf(file_path)

            resumes_data[file_name] = extracted_text

    return resumes_data


if __name__ == "__main__":

    # Folder where all CV PDFs will be stored
    resumes_folder = "data/resumes"

    # Extract text from all CVs inside the folder
    resumes = load_all_resumes(resumes_folder)

    print("\n===== Resume Extraction Summary =====")
    print(f"Total resumes processed: {len(resumes)}")

    # Show preview for each CV
    for file_name, text in resumes.items():
        print("\n------------------------------------")
        print(f"Resume file: {file_name}")
        print(f"Text length: {len(text)} characters")
        print("Preview:")
        print(text[:500])