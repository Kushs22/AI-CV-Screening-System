import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.nyata_guide import ask_both
from src.report import DISCLAIMER, build_docx, build_pdf, split_findings
from src.resume_parser import extract_text
from src.screen import screen_text


SAMPLE_CV = ROOT / "data" / "samples" / "admin_cv.txt"
SAMPLE_JOB = ROOT / "data" / "job_descriptions" / "job_description.txt"
FILE_TYPES = ["pdf", "docx", "txt"]


def _text_from_upload(uploaded) -> str:
    suffix = Path(uploaded.name).suffix.lower() or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(uploaded.getbuffer())
        temp_path = handle.name
    try:
        return extract_text(temp_path)
    finally:
        os.unlink(temp_path)


def _remember_text(slot: str, name: str, text: str, token: str) -> None:
    if st.session_state.get(f"{slot}_token") != token:
        st.session_state.pop("screen_result", None)
    st.session_state[f"{slot}_token"] = token
    st.session_state[f"{slot}_saved_name"] = name
    st.session_state[f"{slot}_saved_text"] = text


def _load_sample() -> None:
    cv = SAMPLE_CV.read_text(encoding="utf-8")
    job = SAMPLE_JOB.read_text(encoding="utf-8")
    st.session_state["cv_paste"] = cv
    st.session_state["job_paste"] = job
    _remember_text("cv", "Sample CV", cv, "sample-cv")
    _remember_text("job", "Sample job", job, "sample-job")
    st.session_state["step"] = 1
    st.session_state["form_error"] = ""
    st.session_state.pop("screen_result", None)


def _goto(step: int) -> None:
    st.session_state["step"] = step
    st.session_state.pop("screen_result", None)
    st.session_state["form_error"] = ""


def _reset() -> None:
    for key in (
        "cv_saved_text",
        "cv_saved_name",
        "cv_token",
        "job_saved_text",
        "job_saved_name",
        "job_token",
        "screen_result",
        "cv_file",
        "job_file",
        "nyata_answers",
        "nyata_question_used",
    ):
        st.session_state.pop(key, None)
    st.session_state["cv_paste"] = ""
    st.session_state["job_paste"] = ""
    st.session_state["nyata_question"] = ""
    st.session_state["step"] = 1
    st.session_state["form_error"] = ""


def _capture(slot: str, uploaded, pasted: str) -> str:
    """Store the file when one is present, otherwise store pasted text."""
    error = ""
    if uploaded is not None:
        token = f"{uploaded.name}:{getattr(uploaded, 'size', 0)}"
        if st.session_state.get(f"{slot}_token") != token:
            try:
                text = _text_from_upload(uploaded)
            except ValueError as exc:
                st.session_state["form_error"] = str(exc)
                return ""
            if not text.strip():
                error = "That file has no readable text. Use a PDF with real text, a Word file, or paste it."
                st.session_state["form_error"] = error
                return ""
            _remember_text(slot, uploaded.name, text, token)
        st.session_state["form_error"] = ""
        return st.session_state.get(f"{slot}_saved_text") or ""
    pasted = (pasted or "").strip()
    if pasted:
        _remember_text(slot, "Pasted text", pasted, f"paste:{hash(pasted)}")
        st.session_state["form_error"] = ""
        return pasted
    return st.session_state.get(f"{slot}_saved_text") or ""


def _steps(current: int) -> None:
    labels = (
        ("1", "Upload CV", "PDF, Word, or text"),
        ("2", "Job description", "Upload or paste"),
        ("3", "Analyse", "Report to download"),
    )
    parts = []
    for number, title, detail in labels:
        index = int(number)
        state = "active" if index == current else "done" if index < current else ""
        parts.append(
            f'<div class="step-pill {state}">'
            f'<span class="step-num">Step {number}</span>'
            f"<strong>{title}</strong>"
            f"<span>{detail}</span>"
            f"</div>"
        )
    st.markdown(f'<div class="step-row">{"".join(parts)}</div>', unsafe_allow_html=True)


def _show_result(result) -> None:
    if result.verdict == "Strong match":
        st.success(result.verdict)
    elif result.verdict == "Good match":
        st.success(result.verdict)
    elif result.verdict in {"Partial match", "Could not verify"}:
        st.warning(result.verdict)
    else:
        st.error(result.verdict)

    lead = result.summary.split(" What is missing")[0].strip()
    st.write(lead)

    metric_cols = st.columns(3)
    metric_cols[0].metric("ATS score", f"{result.fit_score}%")
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

    try:
        docx_bytes = build_docx(result)
        pdf_bytes = build_pdf(result)
    except Exception as exc:  # noqa: BLE001
        st.error(f"The report could not be built. {exc}")
    else:
        word_col, pdf_col = st.columns(2)
        word_col.download_button(
            "Download Word report",
            data=docx_bytes,
            file_name="cv-screening-report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            type="primary",
        )
        pdf_col.download_button(
            "Download PDF report",
            data=pdf_bytes,
            file_name="cv-screening-report.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )

    findings = split_findings(result)
    if result.results:
        st.subheader("Supported")
        if findings["supported"]:
            for item in findings["supported"]:
                st.write(f"**{item.text}**")
                if item.evidence:
                    st.caption(item.evidence)
        else:
            st.write("No required item is fully supported.")

        st.subheader("Missing, and what to add")
        if findings["gaps"]:
            for item in findings["gaps"]:
                st.write(f"**{item.text}**")
                st.write(item.advice or "Add a line that shows this.")
        else:
            st.write("Nothing required is missing.")

        if findings["preferred"]:
            with st.expander("Preferred items still open"):
                for item in findings["preferred"]:
                    st.write(f"**{item.text}**")
                    st.write(item.advice or "Optional. Add a line that shows this if you have it.")

        st.subheader("Line by line")
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

    st.info(DISCLAIMER)
    _show_nyata()


def _nyata_api_key() -> str:
    key = os.environ.get("NYATA_API_KEY", "").strip()
    if key:
        return key
    try:
        return str(st.secrets["NYATA_API_KEY"]).strip()
    except Exception:  # noqa: BLE001
        return ""


def _show_nyata() -> None:
    st.subheader("Where to go next")
    st.write("Looking for jobs related to your field or CV? Find jobs using Nyata.")
    if "nyata_question" not in st.session_state:
        st.session_state["nyata_question"] = ""
    st.text_input(
        "Your question",
        key="nyata_question",
        placeholder="Where can I find jobs related to my CV?",
        label_visibility="collapsed",
    )
    key = _nyata_api_key()
    if not key:
        st.warning("Add the Nyata API key to load these answers.")
        return

    question = (st.session_state.get("nyata_question") or "").strip()
    if st.button("Ask Nyata", type="primary", disabled=not question):
        with st.spinner("Asking Nyata…"):
            st.session_state["nyata_answers"] = ask_both(key, question)

    answers = st.session_state.get("nyata_answers")
    if not answers:
        return
    for item in answers:
        links = item.get("links") or []
        reply = (item.get("reply") or "").strip()
        listings = item.get("listings") or []
        if not links and not reply and not listings and item.get("ok"):
            continue
        st.markdown(f"**{item['title']}**")
        if links:
            for link in links:
                st.link_button(link["name"], link["url"])
        if not item.get("ok"):
            st.write("Nyata could not answer this question just now.")
            continue
        if reply:
            st.write(reply)
        for place in listings:
            line = place["name"]
            if place.get("organisation"):
                line = f"{line} — {place['organisation']}"
            st.write(line)
            detail = ", ".join(
                part
                for part in (place.get("address"), place.get("postcode"), place.get("when"))
                if part
            )
            if place.get("distance_km") is not None:
                detail = f"{detail}, {place['distance_km']:.1f} km away".strip(", ")
            if place.get("open_now"):
                detail = f"{detail} · Open now".strip(" ·")
            if detail:
                st.caption(detail)
            if place.get("directions_url"):
                st.link_button("Directions", place["directions_url"])


st.set_page_config(page_title="AI CV Screening", layout="wide")
st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(900px 280px at 8% -10%, rgba(14, 107, 92, 0.08), transparent 60%),
            #F4F0E8;
        color: #1C2430;
    }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 1.6rem; max-width: 980px; }
    .screen-hero {
        background: #FFFFFF;
        border: 1px solid #E4DCD0;
        border-radius: 16px;
        padding: 1.35rem 1.5rem 1.15rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 2px rgba(28, 36, 48, 0.04);
    }
    .screen-hero h1 {
        margin: 0 0 0.35rem;
        font-size: 2rem;
        letter-spacing: -0.03em;
        color: #14202B;
    }
    .screen-kicker {
        margin: 0 0 0.35rem;
        color: #0E6B5C;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .screen-hero p { margin: 0; color: #3E4C59; line-height: 1.5; }
    .step-row { display: flex; gap: 0.75rem; margin: 0 0 1rem; }
    .step-pill {
        flex: 1;
        background: #FFFFFF;
        border: 1px solid #E4DCD0;
        border-radius: 12px;
        padding: 0.7rem 0.85rem 0.75rem;
    }
    .step-pill strong { display: block; color: #14202B; font-size: 1rem; }
    .step-pill span { display: block; color: #5C6B73; font-size: 0.82rem; }
    .step-num {
        color: #8A8175;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.07em;
        text-transform: uppercase;
    }
    .step-pill.active { border-color: #0E6B5C; box-shadow: inset 0 0 0 1px #0E6B5C; }
    .step-pill.active .step-num, .step-pill.done .step-num { color: #0E6B5C; }
    .step-pill.done { background: #F3F8F6; }
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E4DCD0;
        border-left: 4px solid #0E6B5C;
        border-radius: 12px;
        padding: 0.75rem 0.9rem;
    }
    div[data-testid="stMetricLabel"] { color: #5C6B73; }
    div[data-testid="stMetricValue"] { color: #0E6B5C; }
    [data-testid="stFileUploaderDropzone"] {
        background: #FFFcf8;
        border: 1px dashed #C9BBA8;
        border-radius: 12px;
    }
    .stTextArea textarea {
        background: #FFFFFF;
        border: 1px solid #D9D0C3;
        border-radius: 12px;
        color: #1C2430;
    }
    .stTextArea textarea:focus { border-color: #0E6B5C; box-shadow: 0 0 0 1px #0E6B5C; }
    .stButton > button, .stDownloadButton > button {
        border-radius: 10px;
        border: 1px solid #D9D0C3;
        background: #FFFFFF;
        color: #1C2430;
    }
    .stButton > button[kind="primary"],
    button[data-testid="stBaseButton-primary"],
    .stDownloadButton > button[kind="primary"] {
        background: #0E6B5C;
        border-color: #0E6B5C;
        color: #FFFFFF;
    }
    .stButton > button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover,
    .stDownloadButton > button[kind="primary"]:hover {
        background: #0A5549;
        border-color: #0A5549;
        color: #FFFFFF;
    }
    .stButton > button:disabled,
    .stButton > button[disabled] {
        background: #E7E0D6;
        border-color: #E7E0D6;
        color: #8A8175;
        cursor: not-allowed;
    }
    [data-testid="stAlert"] { border-radius: 12px; }
    [data-testid="stExpander"] {
        background: #FFFFFF;
        border: 1px solid #E4DCD0;
        border-radius: 12px;
    }
    h2, h3 { letter-spacing: -0.02em; color: #14202B; }
    [data-testid="stCaptionContainer"] { color: #3E4C59; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="screen-hero">
      <p class="screen-kicker">Shortlisting aid</p>
      <h1>AI CV Screening</h1>
      <p>Upload a CV, upload the job description, then analyse. The report gives an ATS score for the skills and duties only, and you can download it as Word or PDF.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if "step" not in st.session_state:
    st.session_state["step"] = 1
if "cv_paste" not in st.session_state:
    st.session_state["cv_paste"] = ""
if "job_paste" not in st.session_state:
    st.session_state["job_paste"] = ""

step = int(st.session_state["step"])
_steps(step)
st.button("Try a sample CV and job", on_click=_load_sample)

if st.session_state.get("form_error"):
    st.error(st.session_state["form_error"])

if step == 1:
    st.subheader("1. Upload the CV")
    st.write("Use a PDF, a Word file (.docx), or a plain text file (.txt). You can paste the CV instead.")
    uploaded = st.file_uploader("Upload a CV", type=FILE_TYPES, key="cv_file")
    pasted = st.text_area(
        "Or paste the CV",
        height=220,
        key="cv_paste",
        placeholder="Paste the CV if you do not have a file.",
    )
    ready_text = _capture("cv", uploaded, pasted)
    if st.session_state.get("cv_saved_name") and ready_text.strip():
        st.caption(f"CV ready: {st.session_state['cv_saved_name']}")
    st.button(
        "Continue to the job description",
        type="primary",
        disabled=not ready_text.strip(),
        on_click=_goto,
        args=(2,),
    )

elif step == 2:
    st.subheader("2. Upload the job description")
    st.write("Use a PDF, a Word file (.docx), or a text file. Pasting the posting works as well.")
    if st.session_state.get("cv_saved_name"):
        st.caption(f"CV ready: {st.session_state['cv_saved_name']}")
    uploaded = st.file_uploader(
        "Upload the job description",
        type=FILE_TYPES,
        key="job_file",
    )
    pasted = st.text_area(
        "Or paste the job description",
        height=220,
        key="job_paste",
        placeholder="Paste the full job description.",
    )
    ready_text = _capture("job", uploaded, pasted)
    if st.session_state.get("job_saved_name") and ready_text.strip():
        st.caption(f"Job description ready: {st.session_state['job_saved_name']}")
    back, forward = st.columns(2)
    back.button("Back", on_click=_goto, args=(1,), use_container_width=True)
    forward.button(
        "Continue to analyse",
        type="primary",
        disabled=not ready_text.strip(),
        on_click=_goto,
        args=(3,),
        use_container_width=True,
    )

else:
    st.subheader("3. Analyse and download the report")
    cv_text = st.session_state.get("cv_saved_text") or ""
    job_text = st.session_state.get("job_saved_text") or ""
    st.write(f"**CV:** {st.session_state.get('cv_saved_name') or 'Not added'}")
    st.caption((cv_text[:280] + "…") if len(cv_text) > 280 else cv_text)
    st.write(f"**Job description:** {st.session_state.get('job_saved_name') or 'Not added'}")
    st.caption((job_text[:280] + "…") if len(job_text) > 280 else job_text)

    back, again = st.columns(2)
    back.button("Back", on_click=_goto, args=(2,), use_container_width=True)
    again.button("Start again", on_click=_reset, use_container_width=True)

    if st.button("Analyse", type="primary", disabled=not (cv_text.strip() and job_text.strip())):
        with st.spinner("Checking each skill against the CV…"):
            st.session_state["screen_result"] = screen_text(cv_text, job_text)

    result = st.session_state.get("screen_result")
    if result is not None:
        _show_result(result)
