from jumpTime import milTime, monthToText, timeToEpoch


def test_milTime():
    assert milTime(6, "pm") == 18


def test_monthToText():
    assert monthToText(10) == "October"


def test_timeToEpoch():
    assert timeToEpoch(2023, 10, 1, 1, 00) == 1696143600
