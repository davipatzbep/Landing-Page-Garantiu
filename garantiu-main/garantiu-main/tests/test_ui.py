from datetime import date, datetime, timezone

from garantiu.ui import (
    format_date_br,
    format_datetime_br,
    format_percent,
    format_score,
    risk_level,
)


def test_format_date_br_accepts_iso_date_and_date():
    assert format_date_br("2026-09-10") == "10/09/2026"
    assert format_date_br(date(2026, 1, 2)) == "02/01/2026"


def test_format_datetime_br_converts_utc_and_explicit_offsets():
    assert format_datetime_br("2026-09-10T17:35:00+00:00") == "10/09/2026 14:35"
    assert format_datetime_br("2026-09-10T17:35:00Z") == "10/09/2026 14:35"
    assert format_datetime_br(
        datetime(2026, 9, 10, 17, 35, tzinfo=timezone.utc)
    ) == "10/09/2026 14:35"


def test_format_datetime_br_treats_iso_without_offset_as_utc():
    assert format_datetime_br("2026-09-10T17:35:00") == "10/09/2026 14:35"


def test_temporal_formatters_preserve_invalid_legacy_text():
    assert format_date_br("data antiga") == "data antiga"
    assert format_datetime_br("data antiga") == "data antiga"


def test_score_and_percentage_use_one_decimal_and_brazilian_separator():
    assert format_score(82) == "82,0 / 100"
    assert format_score(82.5) == "82,5 / 100"
    assert format_percent(82.5) == "82,5%"


def test_risk_thresholds_remain_inclusive_at_40_and_70():
    assert risk_level(39.9)[0] == "baixo"
    assert risk_level(40)[0] == "medio"
    assert risk_level(69.9)[0] == "medio"
    assert risk_level(70)[0] == "alto"
