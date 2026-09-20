"""Realistic mock hiring posts across domains and formats."""

MOCK_CANDIDATES: list[dict] = [
    {
        "source": "linkedin",
        "source_url": "https://www.linkedin.com/jobs/view/mock-1001",
        "title_hint": "Graduate Software Engineer",
        "company_hint": "ABC Technologies",
        "location_hint": "Chennai",
        "domain_hint": "Software",
        "posted_offset_hours": 2,
        "application_url": "https://abc-tech.example/careers/grad-se",
        "application_method": "careers_portal",
        "raw_text": (
            "ABC Technologies is hiring Graduate Software Engineers in Chennai. "
            "Fresher / 0-1 years. Engineering graduates 2026 batch welcome. "
            "Apply on our careers portal."
        ),
    },
    {
        "source": "linkedin",
        "source_url": "https://www.linkedin.com/posts/mock-hiring-post-2001",
        "company_hint": "BrightStart Labs",
        "location_hint": "Chennai",
        "domain_hint": "Marketing",
        "posted_offset_hours": 4,
        "application_method": "dm_resume",
        "raw_text": (
            "We are hiring freshers for Digital Marketing Associate roles in Chennai! "
            "DM your resume if you are a 2026 graduate."
        ),
    },
    {
        "source": "linkedin",
        "source_url": "https://www.linkedin.com/posts/mock-walkin-3001",
        "company_hint": "Nova Manufacturing",
        "location_hint": "Chennai",
        "domain_hint": "Operations",
        "posted_offset_hours": 8,
        "application_method": "walk_in",
        "raw_text": (
            "Walk-in interview this Saturday for Production Trainee — freshers only. "
            "Venue: Ambattur, Chennai. Bring resume and ID."
        ),
    },
    {
        "source": "linkedin",
        "source_url": "https://www.linkedin.com/posts/mock-email-4001",
        "company_hint": "DataRiver Analytics",
        "location_hint": "Remote India",
        "domain_hint": "Data Analytics",
        "posted_offset_hours": 12,
        "contact_email": "careers@datariver.example",
        "application_method": "email",
        "raw_text": (
            "Looking for graduates to join our analytics team. Remote India. "
            "Entry level. Send CV to careers@datariver.example with subject Fresher 2026."
        ),
    },
    {
        "source": "linkedin",
        "source_url": "https://www.linkedin.com/posts/mock-form-5001",
        "company_hint": "GreenField NGO",
        "location_hint": "Chennai",
        "domain_hint": "Social Impact",
        "posted_offset_hours": 20,
        "application_url": "https://forms.gle/example-mock-apply",
        "application_method": "google_form",
        "raw_text": (
            "Hiring Program Coordinators — campus / off campus freshers. "
            "Apply using this Google Form. Immediate joiners preferred."
        ),
    },
    {
        "source": "linkedin",
        "source_url": "https://www.linkedin.com/posts/mock-multi-6001",
        "company_hint": "Unified Services Group",
        "location_hint": "Chennai",
        "domain_hint": "BPO",
        "posted_offset_hours": 30,
        "application_method": "phone",
        "raw_text": (
            "We have openings for multiple positions — voice, non-voice, operations. "
            "Freshers welcome. Call +91 98765 43210 or visit our office."
        ),
    },
    {
        "source": "mock_careers",
        "source_url": "https://careers.example.com/jobs/junior-designer-701",
        "title_hint": "Junior UI Designer",
        "company_hint": "PixelCraft Studio",
        "location_hint": "Remote India",
        "domain_hint": "Design",
        "posted_offset_hours": 48,
        "application_url": "https://careers.example.com/jobs/junior-designer-701",
        "application_method": "ats",
        "raw_text": (
            "Junior UI Designer — entry level, portfolio required. Remote India. "
            "0-1 years experience."
        ),
    },
    {
        "source": "mock_careers",
        "source_url": "https://startup.example/jobs/support-associate",
        "title_hint": "Customer Support Associate",
        "company_hint": "HelpHive",
        "location_hint": "Chennai",
        "domain_hint": "Customer Support",
        "posted_offset_hours": 100,
        "application_url": "https://startup.example/jobs/support-associate",
        "application_method": "careers_page",
        "raw_text": "Customer Support Associate — graduate freshers. Chennai office.",
    },
    # Duplicate-ish: same company/title as first job, different URL (for dedup tests in scan)
    {
        "source": "mock_board",
        "source_url": "https://jobsboard.example/view/abc-grad-se-dup",
        "title_hint": "Graduate Software Engineer",
        "company_hint": "ABC Technologies",
        "location_hint": "Chennai",
        "domain_hint": "Software",
        "posted_offset_hours": 3,
        "application_url": "https://abc-tech.example/careers/grad-se",
        "application_method": "careers_portal",
        "raw_text": (
            "ABC Technologies — Graduate Software Engineer, Chennai. Fresher. "
            "Same role posted on our board."
        ),
    },
    # Should be penalized — senior role
    {
        "source": "linkedin",
        "source_url": "https://www.linkedin.com/jobs/view/mock-senior-9001",
        "title_hint": "Senior Engineering Manager",
        "company_hint": "BigCorp",
        "location_hint": "Chennai",
        "domain_hint": "Software",
        "posted_offset_hours": 5,
        "raw_text": "Senior Engineering Manager — 10+ years experience required. Lead a team of 20.",
    },
]
