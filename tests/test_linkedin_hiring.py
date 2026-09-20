from pathlib import Path

from jobfinder.extraction.hiring import analyze_hiring_text, split_multi_role_post
from jobfinder.extraction.linkedin import parse_hiring_post_html, parse_job_detail_html, parse_job_listing_html
from jobfinder.extraction.posted_time import parse_relative_posted
from datetime import datetime, timezone


FIX = Path(__file__).parent / "fixtures" / "linkedin"


def test_hiring_phrases():
    text = "We're hiring freshers in Chennai. DM your resume."
    a = analyze_hiring_text(text, location_hints=["Chennai"])
    assert a.is_hiring_related
    assert a.application_method == "dm_resume"
    assert a.is_fresher


def test_email_resume():
    text = "Hiring graduates. Send your CV to careers@example.com for our engineering team."
    a = analyze_hiring_text(text)
    assert a.is_hiring_related
    assert a.contact_email == "careers@example.com"


def test_multiple_roles():
    text = "We have openings for Java, QA and support. Freshers can apply."
    parts = split_multi_role_post(text)
    assert len(parts) == 3


def test_formal_job_fixture():
    html = (FIX / "job_detail.html").read_text()
    raw = parse_job_detail_html(html, "https://www.linkedin.com/jobs/view/1234567890")
    assert raw is not None
    assert raw.title_hint == "Graduate Engineer"
    assert raw.company_hint == "Example Corp"
    assert raw.posted_at is not None


def test_hiring_post_fixture():
    html = (FIX / "hiring_post.html").read_text()
    posts = parse_hiring_post_html(html, "https://www.linkedin.com/posts/abc", location_hints=["Chennai"])
    assert len(posts) == 1
    assert posts[0].discovery_kind == "hiring_post"


def test_job_search_listing():
    html = (FIX / "job_search.html").read_text()
    items = parse_job_listing_html(html)
    assert len(items) >= 1


def test_relative_time():
    ref = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    dt = parse_relative_posted("2 hours ago", ref)
    assert dt is not None
    assert dt.hour == 10


def test_non_hiring_not_detected():
    a = analyze_hiring_text("Happy weekend everyone!")
    assert not a.is_hiring_related
