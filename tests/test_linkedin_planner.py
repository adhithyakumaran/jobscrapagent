from jobfinder.config import load_profile
from jobfinder.discovery.planner import normalize_query, plan_search_intents


def test_plan_deduplicates_queries():
    profile = load_profile()
    planned = plan_search_intents(profile, budget=100)
    assert planned.deduplicated <= planned.generated
    queries = [normalize_query(i.query_string()) for i in planned.selected]
    assert len(queries) == len(set(queries))


def test_plan_respects_budget():
    profile = load_profile()
    planned = plan_search_intents(profile, budget=12)
    assert len(planned.selected) == 12
