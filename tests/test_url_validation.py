from jobfinder.notifications.telegram import build_inline_keyboard
from jobfinder.models import JobOpportunity
from jobfinder.url_validation import is_valid_apply_url, is_valid_http_url, is_valid_linkedin_url


def test_valid_http_url():
    assert is_valid_http_url("https://example.com/apply")
    assert not is_valid_http_url("")
    assert not is_valid_http_url("mailto:a@b.com")
    assert not is_valid_http_url("/relative/path")
    assert not is_valid_http_url("not a url")


def test_valid_linkedin_url():
    assert is_valid_linkedin_url("https://www.linkedin.com/jobs/view/1")
    assert not is_valid_linkedin_url("https://evil.com/linkedin.com")


def test_valid_apply_url():
    assert is_valid_apply_url("https://careers.example.com/job")
    assert not is_valid_apply_url("careers@example.com")


def test_keyboard_skips_invalid_apply_and_email():
    job = JobOpportunity(
        source="linkedin",
        source_url="https://www.linkedin.com/posts/abc",
        application_url="careers@co.example",
        application_method="email",
        contact_email="careers@co.example",
        description="Email us",
        discovery_kind="hiring_post",
    )
    kb = build_inline_keyboard(job)
    assert kb is not None
    urls = [b["url"] for row in kb["inline_keyboard"] for b in row]
    assert all(u.startswith("http") for u in urls)
    assert "mailto:" not in " ".join(urls)


def test_keyboard_no_buttons_without_valid_urls():
    job = JobOpportunity(
        source="linkedin",
        source_url="",
        application_method="dm_resume",
        description="DM resume",
        discovery_kind="hiring_post",
    )
    assert build_inline_keyboard(job) is None
