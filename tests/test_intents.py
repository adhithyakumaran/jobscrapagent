from jobfinder.config import load_profile
from jobfinder.matching.intents import generate_search_intents


def test_intent_generation_not_empty():
    profile = load_profile()
    intents = generate_search_intents(profile, max_intents=50)
    assert len(intents) == 50
    q = intents[0].query_string()
    assert intents[0].location in q


def test_intent_includes_hiring_and_experience():
    profile = load_profile()
    intents = generate_search_intents(profile, max_intents=1)
    intent = intents[0]
    assert intent.experience_term
    assert intent.hiring_term
