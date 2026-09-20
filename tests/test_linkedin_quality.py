from jobfinder.extraction.hiring import analyze_hiring_text, classify_hiring_signal_strength, split_multi_role_post
from jobfinder.extraction.normalizer import raw_to_opportunity
from jobfinder.extraction.posted_time import parse_relative_posted
from jobfinder.models import RawCandidate
from jobfinder.matching.relevance import RelevanceEngine
from jobfinder.config import load_profile


def test_recruiter_hiring_post():
    text = "I'm Priya, talent acquisition at Acme. We're hiring freshers in Chennai — DM your resume."
    a = analyze_hiring_text(text, location_hints=["Chennai"])
    assert a.is_hiring_related
    assert a.hiring_signal_strength == "high_hiring_signal"
    assert a.application_method == "dm_resume"


def test_company_hiring_post():
    text = "Acme Corp is hiring graduates for our engineering team in Remote India."
    a = analyze_hiring_text(text)
    assert a.is_hiring_related


def test_employee_referral_style():
    text = "My team is hiring! Looking for junior developers — freshers welcome. Comment interested."
    a = analyze_hiring_text(text)
    assert a.hiring_signal_strength in ("high_hiring_signal", "medium_hiring_signal")


def test_walk_in_post():
    text = "Walk-in interview this Saturday for freshers in Chennai campus hiring."
    a = analyze_hiring_text(text)
    assert a.hiring_signal_strength == "high_hiring_signal"


def test_generic_non_hiring_rejected():
    text = "5 career tips for your job search journey. #motivation"
    assert classify_hiring_signal_strength(text) == "low_hiring_signal"
    assert not analyze_hiring_text(text).is_hiring_related


def test_senior_only_low_relevance():
    profile = load_profile()
    engine = RelevanceEngine(profile)
    from jobfinder.models import JobOpportunity

    job = JobOpportunity(
        source="linkedin",
        source_url="https://linkedin.com/posts/senior",
        job_title="Senior Java Architect",
        description="Senior Java Architect — 12 years experience required. Hiring.",
        location="Chennai",
        experience_min=12,
        hiring_signal="hiring_post",
        hiring_signal_strength="medium_hiring_signal",
        discovery_kind="hiring_post",
    )
    score, _, _ = engine.score(job)
    assert score < 30


def test_fresher_java_high_relevance():
    profile = load_profile()
    engine = RelevanceEngine(profile)
    from jobfinder.models import JobOpportunity

    job = JobOpportunity(
        source="linkedin",
        source_url="https://linkedin.com/posts/fresher-java",
        job_title="Java Developer",
        description="Java Developer — freshers welcome — Chennai. Send resume.",
        location="Chennai",
        is_fresher=True,
        hiring_signal_strength="high_hiring_signal",
        discovery_kind="hiring_post",
    )
    score, _, _ = engine.score(job)
    assert score > 40


def test_multiple_roles_split():
    text = "We have openings for Java, QA and .NET roles. Freshers can apply."
    roles = split_multi_role_post(text)
    assert len(roles) == 3


def test_missing_fields_ok():
    raw = RawCandidate(
        source="linkedin",
        source_url="https://www.linkedin.com/posts/xyz",
        raw_text="We're hiring freshers. DM resume.",
        discovery_kind="hiring_post",
    )
    job = raw_to_opportunity(raw)
    assert job.company_name is None or job.company_name
    assert job.posted_at is None
    assert job.hiring_signal_strength == "high_hiring_signal"


def test_missing_posted_time():
    assert parse_relative_posted("unknown date") is None
