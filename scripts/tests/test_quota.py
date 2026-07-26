"""RED (task 2.7): UTC-day healing quota counter.

The counter lives in a file named after the Actions cache key
``heal-quota-<UTC date>``; a new UTC day is a cache miss and resets the
count. Eviction or corruption fails open toward healing (count resets to 0).
"""

from datetime import datetime, timezone

import heal_locator

DAY_ONE = datetime(2026, 7, 26, 10, 30, tzinfo=timezone.utc)
DAY_TWO = datetime(2026, 7, 27, 1, 15, tzinfo=timezone.utc)


def test_cache_key_uses_utc_day():
    assert heal_locator.quota_cache_key(DAY_ONE) == "heal-quota-2026-07-26"
    assert heal_locator.quota_cache_key(DAY_TWO) == "heal-quota-2026-07-27"


def test_missing_file_reads_zero(tmp_path):
    assert heal_locator.read_quota(tmp_path, DAY_ONE) == 0


def test_increment_persists_and_returns_new_count(tmp_path):
    assert heal_locator.increment_quota(tmp_path, DAY_ONE) == 1
    assert heal_locator.increment_quota(tmp_path, DAY_ONE) == 2
    assert heal_locator.read_quota(tmp_path, DAY_ONE) == 2


def test_new_utc_day_resets_count(tmp_path):
    heal_locator.increment_quota(tmp_path, DAY_ONE)
    heal_locator.increment_quota(tmp_path, DAY_ONE)
    assert heal_locator.read_quota(tmp_path, DAY_TWO) == 0


def test_corrupt_file_fails_open(tmp_path):
    (tmp_path / "heal-quota-2026-07-26.txt").write_text("not-a-number", encoding="utf-8")
    assert heal_locator.read_quota(tmp_path, DAY_ONE) == 0


def test_quota_exceeded_at_max_attempts(tmp_path):
    for _ in range(3):
        heal_locator.increment_quota(tmp_path, DAY_ONE)
    assert heal_locator.quota_exceeded(tmp_path, max_attempts=3, now=DAY_ONE)


def test_quota_not_exceeded_below_max(tmp_path):
    for _ in range(2):
        heal_locator.increment_quota(tmp_path, DAY_ONE)
    assert not heal_locator.quota_exceeded(tmp_path, max_attempts=3, now=DAY_ONE)
