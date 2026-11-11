"""Evidence checks for CVs from different fields."""

from __future__ import annotations

from pathlib import Path

from src.jd_parser import parse_job_description
from src.resume_parser import _column_split, _words_to_lines, extract_text
from src.screen import screen_file, screen_text
from src.textutil import tokenize


ROOT = Path(__file__).resolve().parents[1]
OFFICE_JD = (ROOT / "data" / "job_descriptions" / "job_description.txt").read_text()


def _status(result, fragment: str) -> str:
    found = [item for item in result.results if fragment in item.text.lower()]
    assert found, [(item.text, item.status) for item in result.results]
    return found[0].status


def _item(result, fragment: str):
    found = [item for item in result.results if fragment in item.text.lower()]
    assert found, [(item.text, item.status) for item in result.results]
    return found[0]


ADMIN_CV = """
Amira Khan
Housing Officer
amira.khan@example.com

Summary
Housing officer used to busy casework and written updates.

Experience
Housing Officer, Bristol Council
January 2019 - June 2025
Communicated with tenants and wrote clear updates.
Solved problems in rent arrears cases.
Checked applications with a strong eye for detail.
Collaborated with the allocations team.
Met deadlines on weekly case reviews.
Worked independently on a caseload of 80.
Handled tasks efficiently during month end.
Gathered stakeholder requirements for the new rota.
Prepared monthly reports for the management team.
Used Excel and Outlook to track cases.
Contributed to project goals for the quarterly review.

Skills
Adaptable, organized, reliable, quick learner
"""

PLAIN_CV = """
Alex Kim is a warehouse supervisor in Leeds. Alex communicated with clients daily and solved problems in the pick process. Alex worked independently and prepared monthly reports. Alex used Excel. Alex collaborated with the packing team, met deadlines, and handled tasks efficiently. Alex gathered stakeholder requirements and contributed to project goals. Alex is organised, reliable, adaptable, and a quick learner. Attention to detail is central to the stock checks Alex signs off.
"""

SKILLS_ONLY = """
Jordan Lee
Operations coordinator looking for a new role in a busy team.

Skills
communication, problem solving, attention to detail, teamwork, time management, work independently, handling tasks efficiently, stakeholder requirements, monthly reports, digital tools, project goals, adaptable, organised, reliable, quick learner
"""

FLUFFY_CV = """
I am a motivated professional with extensive experience in many environments. I have worked in different roles and I always give my best to every task. I am passionate about success, growth, and making a positive contribution. I have experience working with people and I am keen to develop further. References are available on request from previous managers.
"""

CHEF_CV = """
Jamie Cole
Chef de Partie

Experience
City Bistro, Chef de Partie
March 2021 - November 2024
Prepared lunch and dinner service for 80 covers.
Maintained food hygiene records in the kitchen.
Ordered stock and checked allergen matrices.
Led the evening pastry section.

Skills
Knife skills, food hygiene, allergens, stock control
"""

SOFTWARE_CV = """
Priya Shah
Software Engineer
priya.shah@example.com

Experience
Platform Engineer, Northwind
January 2018 - December 2024
Built REST APIs in Java with Spring Boot.
Wrote unit tests and reviewed pull requests.
Deployed services on Kubernetes.

Skills
Java, Spring Boot, SQL, Git

Education
BSc Computer Science
"""

JAVASCRIPT_CV = """
Sam Okonkwo
Front-end developer

Experience
Built customer portals in JavaScript and React.
Shipped interfaces with HTML and CSS.
Reviewed pull requests with the design team.

Skills
JavaScript, React, HTML, CSS
"""

NURSE_JD = """
Registered Nurse - Acute Ward

Essential:
- NMC registration
- 2 years experience in acute ward nursing
- Medication administration
- Patient observations and vital signs
- Care planning
- Communication with patients and families
- Infection prevention

Desirable:
- Mentoring student nurses
"""

NURSE_CV = """
Hannah Brooks
Registered Nurse
hannah.brooks@example.com

Experience
Staff Nurse, Acute Medical Ward
January 2018 - December 2024
Current NMC registration and revalidation are up to date.
Provided acute ward nursing for medical patients.
Completed medication administration rounds each shift.
Recorded patient observations and vital signs.
Updated care plans for each patient.
Communicated with patients and families during ward rounds.
Followed infection prevention procedures.
Mentored student nurses on the ward.

Education
BSc Nursing
"""

ELECTRICIAN_JD = """
Electrician

Essential:
- City and Guilds electrical installation
- 18th edition wiring regulations
- Testing and inspection
- Fault finding
- Reading technical drawings
- Health and safety
"""

ELECTRICIAN_CV = """
Darren Walsh
Electrician

Experience
Approved Electrician, Hart & Co
February 2015 - August 2024
City and Guilds electrical installation qualified.
Work covered by the 18th edition wiring regulations.
Carried out testing and inspection of consumer units.
Fault finding on domestic and commercial circuits.
Reading technical drawings before first fix.
Followed health and safety on every site.

Skills
2391 inspection, safe isolation
"""

TEACHER_JD = """
Secondary school teacher

Essential:
- QTS
- Lesson planning
- Classroom management
- Assessing student work
- Communication with parents

Desirable:
- A degree in education
"""

TEACHER_CV = """
Leah Morgan
Science Teacher

Experience
Science Teacher, Hillside Academy
September 2017 - July 2025
QTS awarded in 2017.
Prepared lesson plans for year 9 science.
Classroom management of 30 pupils.
Assessing student work against the mark scheme.
Communication with parents at open evening.

Education
BSc Education
"""

JAVA_JD = """
Required:
- Java
- Spring Boot
"""

GO_JD = """
Required:
- Go
"""


def test_office_job_is_split_into_real_requirements():
    requirements = parse_job_description(OFFICE_JD)
    required = [item.text.lower() for item in requirements if item.priority == "required"]
    preferred = [item.text.lower() for item in requirements if item.priority == "preferred"]
    blob = " | ".join(required)
    for phrase in (
        "communication",
        "problem",
        "attention to detail",
        "teamwork",
        "time management",
        "independently",
        "tasks",
        "stakeholder",
        "report",
        "digital",
        "project",
    ):
        assert phrase in blob
    assert "adaptable" in " | ".join(preferred)
    assert "reliable" in " | ".join(preferred)
    assert len(requirements) <= 16


def test_admin_cv_is_a_strong_match_with_evidence():
    result = screen_text(ADMIN_CV, OFFICE_JD)
    assert result.verdict == "Strong match"
    assert result.fit_score >= 80
    assert result.required_coverage >= 80
    communication = _item(result, "communication")
    assert communication.status == "met"
    assert "Communicated with tenants" in communication.evidence
    assert _status(result, "digital") == "met"
    assert _status(result, "adaptable") == "met"


def test_plain_prose_cv_can_match_without_headings():
    result = screen_text(PLAIN_CV, OFFICE_JD)
    assert result.verdict == "Strong match"
    assert result.profile.sections == []


def test_skills_list_alone_is_not_a_strong_match():
    result = screen_text(SKILLS_ONLY, OFFICE_JD)
    assert result.required_coverage >= 80
    assert result.verdict == "Good match"


def test_generic_wording_does_not_score_as_a_match():
    result = screen_text(FLUFFY_CV, OFFICE_JD)
    assert result.verdict == "Weak match"
    assert result.fit_score < 40


def test_chef_does_not_pass_an_office_job():
    result = screen_text(CHEF_CV, OFFICE_JD)
    assert result.verdict == "Weak match"
    assert result.required_coverage < 35


def test_software_cv_does_not_pass_the_office_job():
    result = screen_text(SOFTWARE_CV, OFFICE_JD)
    assert result.verdict in {"Weak match", "Partial match"}
    assert result.required_coverage < 50


def test_nurse_cv_passes_nurse_job_and_software_cv_does_not():
    nurse = screen_text(NURSE_CV, NURSE_JD)
    assert nurse.verdict == "Strong match"
    assert _status(nurse, "nmc") == "met"
    assert _status(nurse, "medication") == "met"
    assert _status(nurse, "acute ward nursing") == "met"
    assert not any("registered nurse -" in item.text.lower() for item in nurse.results)
    assert _status(nurse, "2 years") == "met" or _status(nurse, "years") == "met"
    other = screen_text(SOFTWARE_CV, NURSE_JD)
    assert other.verdict == "Weak match"
    assert _status(other, "nmc") == "missing"
    assert _status(other, "medication") == "missing"


def test_electrician_passes_own_trade_not_a_teacher_cv():
    electrician = screen_text(ELECTRICIAN_CV, ELECTRICIAN_JD)
    assert electrician.verdict == "Strong match"
    assert _status(electrician, "fault") == "met"
    assert _status(electrician, "health and safety") == "met"
    teacher = screen_text(TEACHER_CV, ELECTRICIAN_JD)
    assert teacher.verdict == "Weak match"


def test_teacher_passes_teaching_job():
    result = screen_text(TEACHER_CV, TEACHER_JD)
    assert result.verdict == "Strong match"
    assert _status(result, "qts") == "met"
    assert _status(result, "degree") == "met"


def test_javascript_does_not_satisfy_java():
    result = screen_text(JAVASCRIPT_CV, JAVA_JD)
    assert _status(result, "java") == "missing"
    assert _item(result, "java").text.lower() == "java"
    java = screen_text(SOFTWARE_CV, JAVA_JD)
    assert _status(java, "java") == "met"
    assert _status(java, "spring") == "met"


def test_go_does_not_match_going_or_a_casual_use():
    casual = """
    Riley Chen
    Retail assistant who likes going the extra mile for regular customers.
    Experience
    Shop Assistant
    I will go the extra mile on every shift and I keep the stockroom tidy for the team.
    I am going to keep learning the till system and helping on the shop floor each week.
    """
    missed = screen_text(casual, GO_JD)
    assert _status(missed, "go") == "missing"
    skilled = casual + "\nSkills\nGo, SQL\n"
    # The casual CV still contains the unsupported sentence, but the skills line is allowed.
    hit = screen_text(skilled, GO_JD)
    assert _status(hit, "go") == "met"


def test_cplusplus_does_not_match_the_letter_c():
    cv = """
    Chris Adeyemi
    Software engineer writing services and tools for internal platforms.
    Experience
    Developer
    January 2016 - January 2024
    Built services in C++ for the pricing engine and maintained the build scripts.
    """
    result = screen_text(cv, "Required:\n- C++\n- C\n")
    assert _status(result, "c++") == "met"
    letter = [item for item in result.results if item.text.strip().lower() == "c"]
    assert letter and letter[0].status == "missing"


def test_words_on_different_lines_are_not_combined():
    cv = """
    Case worker covering housing repairs and tenant appointments across the city.
    Experience
    Officer
    January 2020 - January 2024
    Stakeholder updates
    System requirements
    """
    result = screen_text(cv, "Required:\n- stakeholder requirements\n")
    assert _status(result, "stakeholder") == "missing"
    together = cv.replace(
        "Stakeholder updates\n    System requirements",
        "Gathered stakeholder requirements for the new rota",
    )
    matched = screen_text(together, "Required:\n- stakeholder requirements\n")
    assert _status(matched, "stakeholder") == "met"


def test_british_spelling_matches_american_spelling():
    cv = """
    Nia Roberts keeps records for a legal team and writes correspondence each day.
    Experience
    Assistant
    I organised the archive and the hearing bundles for three solicitors.
    """
    result = screen_text(cv, "Required:\n- organized\n")
    assert _status(result, "organized") == "met"


def test_years_are_counted_from_dates_and_left_unverified_when_absent():
    dated = """
    Jo Patel
    Analyst
    Experience
    Analyst, Example Ltd
    January 2016 - December 2024
    Built monthly packs for the finance team and checked the source figures.
    """
    hit = screen_text(dated, "Required:\n- 5 years experience in reporting\n")
    years = _item(hit, "years")
    assert years.status == "met"
    undated = """
    Jo Patel is an analyst who builds monthly packs for the finance team and checks the source figures with care every week.
    """
    missed = screen_text(undated, "Required:\n- 5 years experience in reporting\n")
    assert _item(missed, "years").status == "unverified"
    assert missed.required_unverified == 1


def test_short_experience_does_not_meet_a_five_year_requirement():
    cv = """
    Jo Patel
    Analyst
    Experience
    Analyst, Example Ltd
    March 2025 - November 2025
    Built monthly packs for the finance team and checked the source figures.
    """
    result = screen_text(cv, "Required:\n- 5 years experience\n")
    assert _item(result, "years").status == "missing"


def test_higher_degree_in_the_same_subject_counts_and_the_wrong_subject_does_not():
    jd = "Essential:\n- Bachelor's degree in nursing\n"
    higher = """
    Hannah Brooks
    Nurse
    Education
    MSc Nursing
    Experience
    Staff nurse on a medical ward from 2019 until 2024, caring for acute patients.
    """
    assert _status(screen_text(higher, jd), "nursing") == "met"
    other = """
    Priya Shah
    Engineer
    Education
    BSc Computer Science
    Experience
    Built software for hospital scheduling from 2019 until 2024 and supported the ward clerks.
    """
    assert _status(screen_text(other, jd), "nursing") == "missing"


def test_unreadable_cv_is_not_given_a_low_match():
    result = screen_text("   ", OFFICE_JD)
    assert result.readable is False
    assert result.verdict == "Could not read this CV"
    assert result.fit_score == 0


def test_managed_and_manage_share_a_stem():
    assert tokenize("managed the nurses") 
    assert set(tokenize("managed")).intersection(tokenize("manage"))


def test_pdf_and_docx_text_is_read(tmp_path: Path):
    pdf_path = tmp_path / "cv.pdf"
    _write_pdf(
        pdf_path,
        [
            "Amira Khan",
            "Housing Officer with casework experience across the city.",
            "Communicated with tenants and prepared monthly reports.",
            "Used Excel to track open cases and met deadlines each week.",
        ],
    )
    text = extract_text(str(pdf_path))
    assert "Communicated with tenants" in text
    job = "Required:\n- communication\n- monthly reports\n"
    assert _status(screen_file(str(pdf_path), job), "communication") == "met"

    from docx import Document

    docx_path = tmp_path / "cv.docx"
    document = Document()
    document.add_paragraph("Amira Khan")
    document.add_paragraph(
        "Housing officer who communicated with tenants and prepared monthly reports using Excel."
    )
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Skills"
    table.rows[0].cells[1].text = "Excel, casework"
    document.save(docx_path)
    docx_text = extract_text(str(docx_path))
    assert "monthly reports" in docx_text
    assert "Excel" in docx_text


def test_right_aligned_dates_are_not_treated_as_a_second_column():
    words = []
    for index in range(8):
        top = 100 + index * 16
        words.append({"text": "Managed", "x0": 72, "x1": 130, "top": top})
        words.append({"text": "ward", "x0": 136, "x1": 170, "top": top})
        words.append({"text": "rounds", "x0": 176, "x1": 230, "top": top})
    words.append({"text": "2020", "x0": 480, "x1": 520, "top": 100})
    assert _column_split(words) is None


def test_a_lowercase_skill_list_is_not_treated_as_experience():
    text = clean_text_for_test()
    assert "\n" in text
    assert text.splitlines()[0] == "Skills"


def clean_text_for_test() -> str:
    from src.resume_parser import clean_text

    return clean_text("Skills\ncommunication, problem solving, teamwork\n")


def test_partial_duty_names_the_missing_words():
    cv = """
    Ava Cole is a retail assistant in Bristol and is available for weekday shifts throughout the year.
    Experience
    Retail assistant, Bristol
    January 2023 - June 2024
    Served customers in a friendly and professional manner during busy trading periods on the shop floor.
    """
    result = screen_text(
        cv,
        "Required:\n- serve food and beverages to guests in a friendly and professional manner\n",
    )
    item = result.results[0]
    assert item.status == "partial"
    assert "food" in item.advice.lower()
    assert "beverage" in item.advice.lower()
    assert "add a line" in item.advice.lower()


def test_missing_requirement_says_what_to_add():
    result = screen_text(SOFTWARE_CV, NURSE_JD)
    item = _item(result, "medication")
    assert item.status == "missing"
    assert "medication" in item.advice.lower()
    assert item.advice.lower().startswith("not in the cv")


def test_a_wrapped_line_still_matches_health_and_safety():
    cv = """
    Experience
    Support worker
    March 2023 - May 2024
    Completed mandatory training including safeguarding, manual handling, and health and
    safety procedures on every shift.
    """
    result = screen_text(cv, "Required:\n- comply with health and safety regulations\n")
    assert _status(result, "health and safety") == "met"


def test_named_degrees_do_not_match_a_different_subject():
    law = """
    Amira Shah completed a training seat in a commercial firm and kept a full caseload of matters.
    Education
    LLB Law, a qualifying law degree
    Experience
    Trainee solicitor from 2021 until 2024, attending court and preparing bundles for counsel.
    """
    computer = """
    Priya Shah builds internal tools for a software team and supports the release process each week.
    Education
    BSc Computer Science
    Experience
    Built services from 2021 until 2024 and maintained the deployment scripts for the platform.
    """
    jd = "Essential:\n- qualifying law degree\n"
    assert _status(screen_text(law, jd), "law") == "met"
    assert _status(screen_text(computer, jd), "law") == "missing"


def test_each_field_matches_its_own_work_and_not_another_field():
    psychology_cv = """
    Experience
    Assistant Psychologist, Community Team
    September 2021 - August 2025
    Delivered cognitive behavioural therapy sessions each week.
    Completed a risk assessment before every appointment.
    Wrote clinical notes after each contact.
    Education
    BPS accredited psychology degree
    """
    psychology_jd = """
    Assistant Psychologist
    Essential:
    - cognitive behavioural therapy
    - risk assessment
    - clinical notes
    - BPS accredited psychology degree
    """
    law_cv = """
    Experience
    Paralegal, City Firm
    June 2020 - May 2024
    Legal research for three commercial disputes.
    Drafting contracts for supplier agreements.
    Client interviews before each hearing.
    Education
    Qualifying law degree
    """
    law_jd = """
    Paralegal
    Essential:
    - legal research
    - drafting contracts
    - client interviews
    - qualifying law degree
    """
    engineering_cv = """
    Experience
    Mechanical Design Engineer
    January 2018 - December 2024
    Produced technical drawings in CAD for gearbox housings.
    Tolerance analysis on each mating face.
    Design for manufacture reviews with the machine shop.
    """
    engineering_jd = """
    Mechanical design engineer
    Essential:
    - CAD
    - tolerance analysis
    - design for manufacture
    - technical drawings
    """
    finance_cv = """
    Experience
    Financial Analyst
    April 2019 - March 2025
    Built the financial modelling for the quarterly forecast.
    Variance analysis against the management accounts.
    Used Excel to prepare the board pack.
    """
    finance_jd = """
    Financial analyst
    Essential:
    - financial modelling
    - variance analysis
    - management accounts
    - Excel
    """
    business_cv = """
    Experience
    Business Analyst
    February 2019 - January 2025
    Requirements gathering with the operations managers.
    Process mapping of the order-to-cash flow.
    Ran stakeholder workshops and wrote the user stories.
    """
    business_jd = """
    Business analyst
    Essential:
    - requirements gathering
    - process mapping
    - stakeholder workshops
    - user stories
    """
    computer_cv = """
    Experience
    Software Engineer
    January 2018 - December 2024
    Wrote Python services and covered data structures in the design notes.
    Unit testing on every module.
    Published REST APIs for the billing service.
    """
    computer_jd = """
    Software engineer
    Essential:
    - Python
    - data structures
    - unit testing
    - REST APIs
    """
    own = [
        (psychology_cv, psychology_jd, "cognitive"),
        (law_cv, law_jd, "drafting"),
        (engineering_cv, engineering_jd, "tolerance"),
        (finance_cv, finance_jd, "variance"),
        (business_cv, business_jd, "process mapping"),
        (computer_cv, computer_jd, "unit testing"),
    ]
    for cv, jd, fragment in own:
        result = screen_text(cv, jd)
        assert result.verdict in {"Strong match", "Good match"}, (fragment, result.verdict, result.fit_score)
        assert _status(result, fragment) == "met"
    assert screen_text(psychology_cv, law_jd).verdict == "Weak match"
    assert screen_text(computer_cv, psychology_jd).verdict == "Weak match"
    assert screen_text(finance_cv, engineering_jd).verdict == "Weak match"
    assert _status(screen_text(law_cv, finance_jd), "variance") == "missing"


def test_company_copy_is_not_scored_as_a_cv_requirement():
    job = """
    About UsSAH Diagnostics is a growing healthcare provider dedicated to delivering high-quality diagnostic services.
    We pride ourselves on compassionate patient care and professional excellence.
    roleWe are building an AI skin cancer classification model.
    Part-time hours possible.
    What you will do
    Train and fine-tune deep-learning classifiers on multi-view image sets.
    Find which images and combinations work best (each view alone and combined).
    Measure sensitivity, specificity, PPV, and calibration.
    You have the right to work in the UK. We cannot offer visa sponsorship.
    It helps if you have
    A deep-learning project on skin lesion images.
    """
    requirements = parse_job_description(job)
    blob = " | ".join(item.text.lower() for item in requirements)
    assert "about us" not in blob
    assert "pride" not in blob
    assert "part-time" not in blob
    assert "visa" not in blob
    assert "right to work" not in blob
    assert "what you will do" not in blob
    assert "it helps if you have" not in blob
    assert "fine-tune" in blob or "fine tune" in blob
    assert "sensitivity" in blob
    images = [item.text.lower() for item in requirements if "images" in item.text.lower() and "combinations" in item.text.lower()]
    assert images
    project = [item for item in requirements if "deep-learning project" in item.text.lower() or "skin lesion" in item.text.lower()]
    assert project and project[0].priority == "preferred"


def test_a_real_two_column_page_is_split():
    words = []
    for index in range(8):
        top = 80 + index * 18
        words.append({"text": "Nurse", "x0": 40, "x1": 80, "top": top})
        words.append({"text": "medication", "x0": 86, "x1": 160, "top": top})
        words.append({"text": "Teacher", "x0": 340, "x1": 400, "top": top})
        words.append({"text": "lessons", "x0": 406, "x1": 470, "top": top})
    assert _column_split(words) is not None
    left = [word for word in words if word["x0"] < 300]
    assert "Nurse" in _words_to_lines(left)


def _write_pdf(path: Path, lines: list[str]) -> None:
    commands = ["BT", "/F1 12 Tf", "72 740 Td", "16 TL"]
    for index, line in enumerate(lines):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index:
            commands.append("T*")
        commands.append(f"({safe}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    chunks = [b"%PDF-1.4\n"]
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
    xref = sum(len(chunk) for chunk in chunks)
    xref_rows = ["xref", f"0 {len(objects) + 1}", "0000000000 65535 f "]
    for offset in offsets[1:]:
        xref_rows.append(f"{offset:010d} 00000 n ")
    trailer = (
        "\n".join(xref_rows)
        + f"\ntrailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    )
    path.write_bytes(b"".join(chunks) + trailer.encode("ascii"))


