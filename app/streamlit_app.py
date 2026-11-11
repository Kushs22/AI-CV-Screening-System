import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.screen import screen_file, screen_text


SAMPLE_CV = ROOT / "data" / "samples" / "admin_cv.txt"
SAMPLE_JOB = ROOT / "data" / "job_descriptions" / "job_description.txt"


def _load_sample() -> None:
    st.session_state["cv_text"] = SAMPLE_CV.read_text(encoding="utf-8")
    st.session_state["job_text"] = SAMPLE_JOB.read_text(encoding="utf-8")


st.set_page_config(page_title="AI CV Screening", layout="wide")
st.title("AI CV Screening")
st.write(
    "Each requirement in the job description is checked against the CV on its own. "
    "A requirement counts as met only when one line of the CV contains evidence for it. "
    "The same check is used for every field: the job text decides what is being looked for."
)

st.button("Load sample CV and job", on_click=_load_sample)
uploaded = st.file_uploader("Upload a CV", type=["pdf", "docx", "txt"])
pasted_cv = st.text_area(
    "Or paste CV text",
    height=180,
    key="cv_text",
    placeholder="Paste the CV if you do not have a file.",
)
job_description = st.text_area(
    "Paste the job description",
    height=220,
    key="job_text",
    placeholder="Paste the full job description.",
)

if st.button("Analyse CV", type="primary"):
    if not job_description.strip():
        st.warning("Paste a job description first.")
    elif uploaded is None and not pasted_cv.strip():
        st.warning("Upload a CV or paste the CV text.")
    else:
        if uploaded is not None:
            suffix = Path(uploaded.name).suffix.lower() or ".pdf"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                handle.write(uploaded.getbuffer())
                temp_path = handle.name
            try:
                result = screen_file(temp_path, job_description)
            finally:
                os.unlink(temp_path)
        else:
            result = screen_text(pasted_cv, job_description)

        if result.verdict == "Strong match":
            st.success(result.verdict)
        elif result.verdict == "Good match":
            st.success(result.verdict)
        elif result.verdict in {"Partial match", "Could not verify"}:
            st.warning(result.verdict)
        else:
            st.error(result.verdict)

        st.write(result.summary)

        metric_cols = st.columns(3)
        metric_cols[0].metric("Job fit", f"{result.fit_score}%")
        metric_cols[1].metric(
            "Required items met",
            f"{result.required_met}/{result.required_total}",
        )
        preferred = (
            f"{result.preferred_met}/{result.preferred_total}"
            if result.preferred_total
            else "None listed"
        )
        metric_cols[2].metric("Preferred items met", preferred)

        if result.results:
            order = ["met", "partial", "missing", "unverified"]
            counts = [
                sum(1 for item in result.results if item.status == status)
                for status in order
            ]
            st.subheader("Requirement results")
            st.bar_chart(
                pd.DataFrame(
                    {
                        "Result": ["Met", "Partial", "Missing", "Unverified"],
                        "Count": counts,
                    }
                ),
                x="Result",
                y="Count",
            )
            st.dataframe(
                [
                    {
                        "Requirement": item.text,
                        "Priority": item.priority,
                        "Result": item.status,
                        "Match": item.match_type,
                        "Evidence from the CV": item.evidence,
                    }
                    for item in result.results
                ],
                use_container_width=True,
                hide_index=True,
            )

        profile = result.profile
        if profile is not None:
            with st.expander("What was read from the CV"):
                sections = ", ".join(profile.sections) if profile.sections else "No section headings found"
                st.write(f"Words read: {profile.word_count}")
                st.write(f"Sections: {sections}")
                if profile.email:
                    st.write(f"Email found: {profile.email}")
                if profile.years_experience is not None:
                    st.write(
                        f"Employment dates add up to about {profile.years_experience} years."
                    )
                st.text(profile.text or "No text could be extracted.")

        st.info(
            "This score is evidence for a shortlist. It is not a hiring decision, "
            "and it is not a prediction of one employer's applicant tracking system."
        )
