"""
Author: Sourcery
Co-Author: Ian Young

Purpose: Test to see if the URLs that require dynamic org IDs may be
retrieved.
"""

import pytest
from tools.api_endpoints import set_org_id, get_url


@pytest.mark.parametrize(
    "org_id, expected",
    [
        (
            "123",
            {
                "DESK_DECOM": "https://api.verkada.com/vinter/v1/user/async/\
organization/123/device/",
                "GUEST_IPADS_DECOM": "https://vdoorman.command.verkada.com/\
device/org/123/site/",
                "GUEST_PRINTER_DECOM": "https://vdoorman.command.verkada.com/\
printer/org/123/site/",
                "DESK_URL": "https://api.verkada.com/vinter/v1/user/\
organization/123/device",
                "IPAD_URL": "https://vdoorman.command.verkada.com/site/\
settings/v2/org/123/site/",
                "ACCESS_LEVELS": "https://vcerberus.command.verkada.com/\
organizations/123/schedules",
                "ACL_DECOM": "https://vcerberus.command.verkada.com/\
organizations/123/schedules",
            },
        ),
        (
            "456",
            {
                "DESK_DECOM": "https://api.verkada.com/vinter/v1/user/async/\
organization/456/device/",
                "GUEST_IPADS_DECOM": "https://vdoorman.command.verkada.com/\
device/org/456/site/",
                "GUEST_PRINTER_DECOM": "https://vdoorman.command.verkada.com/\
printer/org/456/site/",
                "DESK_URL": "https://api.verkada.com/vinter/v1/user/\
organization/456/device",
                "IPAD_URL": "https://vdoorman.command.verkada.com/site/\
settings/v2/org/456/site/",
                "ACCESS_LEVELS": "https://vcerberus.command.verkada.com/\
organizations/456/schedules",
                "ACL_DECOM": "https://vcerberus.command.verkada.com/\
organizations/456/schedules",
            },
        ),
    ],
    ids=["org_id_123", "org_id_456"],
)
def test_set_org_id(org_id, expected):
    """
    Test the set_org_id function.

    This test function uses pytest to parametrize different organization
    IDs and their expected results to verify the set_org_id function.

    Args:
        org_id: The organization ID to be tested.
        expected: The expected dictionary of URLs associated with the
                organization ID.

    Returns:
        None
    """

    # Act
    result = set_org_id(org_id)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    "name, org_id, expected",
    [
        (
            "DESK_DECOM",
            "123",
            "https://api.verkada.com/vinter/v1/user/async/organization/123/device/",
        ),
        (
            "GUEST_IPADS_DECOM",
            "123",
            "https://vdoorman.command.verkada.com/device/org/123/site/",
        ),
        ("INVALID_NAME", "123", None),
    ],
    ids=[
        "valid_name_desk_decom",
        "valid_name_guest_ipads_decom",
        "invalid_name",
    ],
)
def test_get_url(name, org_id, expected):
    """
    Test the get_url function.

    This test function uses pytest to parametrize different names and
    organization IDs to verify the get_url function.

    Args:
        name: The name used to retrieve the URL.
        org_id: The organization ID to be set.
        expected: The expected URL associated with the provided name.

    Returns:
        None
    """

    # Act
    result = get_url(name, org_id)

    # Assert
    assert result == expected
