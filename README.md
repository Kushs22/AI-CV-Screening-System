# AI CV Screening

Score any CV against any job description. The job is split into separate requirements. A requirement counts as met only when one line of the CV contains evidence for it, and the result shows that line.

It works across fields. A nursing CV, a teaching CV, an electrician’s CV, and a software CV are all checked against the wording of the job in front of them. There is no fixed skill list.

## What you get

- A verdict: strong, good, partial, or weak match
- A job-fit score based on how well the required items are supported
- Every requirement marked met, partial, missing, or unverified
- The CV line used as evidence
- Years of experience read from employment dates, when the dates can be read
- Qualification checks, including subject, when the job asks for one

A list of skills with no experience behind it can score as a good match. It does not score as a strong match. A PDF with no text layer is reported as unreadable instead of being given a low score.

This is a shortlisting aid. It is not a hiring decision, and it does not predict one employer’s applicant tracking system.

## Run it

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501).

Upload a PDF, DOCX, or TXT CV, or paste the text. Paste the job description and choose Analyse CV.

Score one file from the terminal:

```bash
python -m src.screen data/samples/admin_cv.txt data/job_descriptions/job_description.txt
```

## How a requirement is matched

The job text supplies the requirements, split into required and preferred items. Each one is compared with a single CV line.

A match can be the same wording, a normal variant such as organised and organized, or a direct equivalent such as Excel for digital tools. Words taken from two different lines are not combined. Java does not match JavaScript, and Go does not match going.

Years are read from employment dates. A higher qualification covers a lower one in the same subject.

## Tests

```bash
pytest
```

The tests include office, nursing, electrical, and teaching CVs, plus CVs that should not pass the job they are checked against.
