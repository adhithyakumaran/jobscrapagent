from datetime import timedelta

from jobfinder.freshness import freshness_bucket, utc_now
from jobfinder.models import FreshnessBucket


def test_freshness_buckets():
    now = utc_now()
    assert freshness_bucket(now - timedelta(hours=2), now) == FreshnessBucket.VERY_NEW
    assert freshness_bucket(now - timedelta(hours=12), now) == FreshnessBucket.NEW
    assert freshness_bucket(now - timedelta(days=2), now) == FreshnessBucket.RECENT
    assert freshness_bucket(now - timedelta(days=5), now) == FreshnessBucket.OLDER
