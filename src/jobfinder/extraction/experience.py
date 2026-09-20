from jobfinder.extraction.patterns import EXP_MIN_RE, EXP_RANGE_RE, FRESHER_RE


def parse_experience(text: str) -> tuple[int | None, int | None, bool, bool]:
    is_fresher = bool(FRESHER_RE.search(text))
    is_entry = is_fresher or "entry" in text.lower() or "junior" in text.lower()
    exp_min, exp_max = None, None
    m = EXP_RANGE_RE.search(text)
    if m:
        exp_min, exp_max = int(m.group(1)), int(m.group(2))
    else:
        m2 = EXP_MIN_RE.search(text)
        if m2:
            exp_min = int(m2.group(1))
    if is_fresher and exp_max is None:
        exp_max = 1
        exp_min = 0
    return exp_min, exp_max, is_fresher, is_entry
