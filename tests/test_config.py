from pathlib import Path

from jobfinder.config import is_any, load_profile


def test_load_profile():
    profile = load_profile(Path(__file__).resolve().parents[1] / "config" / "profile.yaml")
    assert profile.candidate.education.graduation_year == 2026
    assert "Chennai" in profile.candidate.locations
    assert is_any(profile.candidate.target_domains)


def test_is_any():
    assert is_any(["any"])
    assert is_any(["Software", "any"])
    assert not is_any(["Software"])
