import pytest
from datetime import datetime
from app.scraper.aggregators import convert_to_datetime, verify_date_series
from app.utils.datetime import as_utc, as_vu_to_utc


@pytest.mark.parametrize(
    "date_string, issued_at, expected_dt",
    [
        # Test a date string that is in the current month and after the issued_at date
        ("Sat 06", datetime(2023, 5, 5), datetime(2023, 5, 6)),
        # Test a date string that is in the current month and before the issued_at date NOTE impossible to know from a single instance
        # ("Thu 04", datetime(2023, 5, 5), datetime(2023, 5, 4)),
        # Test a date string that is in the next month and after the issued_at date
        ("Mon 01", datetime(2023, 4, 29), datetime(2023, 5, 1)),
        # Test a date string with a day of the month equal to the last day of the current month
        ("Sat 31", datetime(2022, 12, 1), datetime(2022, 12, 31)),
        # Test a date string with a day of the month equal to the first day of the next month
        ("Sun 01", datetime(2022, 12, 31), datetime(2023, 1, 1)),
    ],
)
def test_convert_to_datetime(date_string, issued_at, expected_dt):
    utc_vu_dt = convert_to_datetime(date_string, as_vu_to_utc(issued_at))
    utc_expected_dt = as_vu_to_utc(expected_dt)
    assert utc_vu_dt == utc_expected_dt


@pytest.mark.parametrize(
    "date_series, expected",
    [
        # Test a normal sequential datetime series
        (
            [
                datetime(2023, 1, 1),
                datetime(2023, 1, 2),
                datetime(2023, 1, 3),
                datetime(2023, 1, 4),
                datetime(2023, 1, 5),
            ],
            [
                datetime(2023, 1, 1),
                datetime(2023, 1, 2),
                datetime(2023, 1, 3),
                datetime(2023, 1, 4),
                datetime(2023, 1, 5),
            ],
        ),
        # Test a series that has the first item shifted to the next month - due to issued_at date being later than the first date in the list
        (
            [
                datetime(2023, 2, 1),
                datetime(2023, 1, 2),
                datetime(2023, 1, 3),
                datetime(2023, 1, 4),
                datetime(2023, 1, 5),
            ],
            [
                datetime(2023, 1, 1),
                datetime(2023, 1, 2),
                datetime(2023, 1, 3),
                datetime(2023, 1, 4),
                datetime(2023, 1, 5),
            ],
        ),
        # Test a series that crosses a month boundary
        (
            [
                datetime(2023, 1, 29),
                datetime(2023, 1, 30),
                datetime(2023, 1, 31),
                datetime(2023, 2, 1),
                datetime(2023, 2, 2),
            ],
            [
                datetime(2023, 1, 29),
                datetime(2023, 1, 30),
                datetime(2023, 1, 31),
                datetime(2023, 2, 1),
                datetime(2023, 2, 2),
            ],
        ),
    ],
)
def test_sequential_datetimes(date_series, expected):
    fixed_dates = verify_date_series(date_series)
    assert len(fixed_dates) == len(expected)
    for d, dd in zip(fixed_dates, expected):
        assert d == dd
