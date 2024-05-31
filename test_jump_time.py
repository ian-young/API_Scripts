"""
Author: Ian Young
Purpose: Test the jump_time module to make sure it is returning the expected
values.
"""
from jump_time import mil_time, month_to_text, time_to_epoch


def test_mil_time():
    """Test if jump_time can convert from 12-hour to 24-hour format."""
    assert mil_time(6, "pm") == 18


def test_month_to_text():
    """Test if jump_time can convert an integer to a month."""
    assert month_to_text(10) == "October"


def test_time_to_epoch():
    """Test if jump_time can convert date & time to an epoch timestamp."""
    assert time_to_epoch(2023, 10, 1, 1, 00) == 1696143600
