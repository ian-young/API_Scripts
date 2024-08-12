"""
Author: Ian Young
Purpose: A large sequence of variables with URLs that may be imported
for easy and clean scripting.
"""

##############################################################################
#############################  Native Endpoints  #############################
##############################################################################

# Base Variables
BASE_URL = "https://api.verkada.com/"
CAM = "cameras/v1/"
CORE = "core/v1/"
AC = "access/v1/"
SV = "environment/v1/"
GUEST = "guest/v1/"
ALARM = "alarms/v1/"
EVENT = "events/v1/"
VX = "viewing_station/v1/"

## Camera API
GET_ALERTS = f"{BASE_URL}{CAM}alerts"
GET_SEEN_PLATES = f"{BASE_URL}{CAM}analytics/lpr/images"
DELETE_LPOI = f"{BASE_URL}{CAM}analytics/lpr/license_plate_of_interest"
UPDATE_LPOI = f"{BASE_URL}{CAM}analytics/lpr/license_plate_of_interest"
CREATE_LPOI = f"{BASE_URL}{CAM}analytics/lpr/license_plate_of_interest"
GET_PLATE_TIMESTAMP = f"{BASE_URL}{CAM}analytics/lpr/timestamps"
GET_MAX_PEP_VEH_COUNTS = f"{BASE_URL}{CAM}analytics/max_object_counts"
GET_PEP_VEH_COUNTS = f"{BASE_URL}{CAM}analytics/object_counts"
MQTT_CONFIG = f"{BASE_URL}{CAM}analytics/object_position_mqtt"
GET_AUDIO_STATUS = f"{BASE_URL}{CAM}audio/status"
UPDATE_AUDIO_STATUS = f"{BASE_URL}{CAM}audio/status"
GET_CB = f"{BASE_URL}{CAM}cloud_backup/settings"
UPDATE_CB = f"{BASE_URL}{CAM}cloud_backup/settings"
GET_CAMERA_DATA = f"{BASE_URL}{CAM}devices"
GET_FOOTAGE_LINK = f"{BASE_URL}{CAM}footage/link"
GET_THUMB_IMG = f"{BASE_URL}{CAM}footage/thumbnails?resolution=low-res"
GET_THUMB_LINK = f"{BASE_URL}{CAM}footage/thumbnails/link?expiry=86400"
GET_STREAM_TOKEN = f"{BASE_URL}{CAM}footage/token"
STREAM_FOOTAGE = f"{BASE_URL}stream/{CAM}footage/stream/key?transcode=false"
DELETE_POI = f"{BASE_URL}{CAM}people/person_of_interest"
GET_ALL_POI = f"{BASE_URL}{CAM}people/person_of_interest"
UPDATE_POI = f"{BASE_URL}{CAM}people/person_of_interest"
CREATE_POI = f"{BASE_URL}{CAM}people/person_of_interest"
GET_ALL_LPOI = f"{BASE_URL}{CAM}analytics/lpr/license_plate_of_interest"
GET_TREND_DATA = f"{BASE_URL}{CAM}analytics/occupancy_trends?interval=1_hour"
GET_LATEST_THUMB_IMG = (
    f"{BASE_URL}{CAM}footage/thumbnails/latest?resolution=low-res"
)

## Core API
GET_AUDIT_LOGS = f"{BASE_URL}{CORE}audit_log"
DELETE_USER = f"{BASE_URL}{CORE}user"
GET_USER = f"{BASE_URL}{CORE}user"
CREATE_USER = f"{BASE_URL}{CORE}user"
UPDATE_USER = f"{BASE_URL}{CORE}user"

## Access API
GET_ALL_AC_GROUPS = f"{BASE_URL}{AC}access_groups"
DELETE_AC_GROUP = f"{BASE_URL}{AC}access_groups/group"
GET_AC_GROUP = f"{BASE_URL}{AC}access_groups/group"
CREATE_AC_GROUP = f"{BASE_URL}{AC}access_groups/group"
REMOVE_USR_FROM_AC_GROUP = f"{BASE_URL}{AC}access_groups/group/user"
ADD_USR_TO_AC_GROUP = f"{BASE_URL}{AC}access_groups/group/user"
GET_ALL_AC_USRS = f"{BASE_URL}{AC}access_users"
GET_AC_INFO_OBJ = f"{BASE_URL}{AC}access_users/user"
ACTIVATE_AC_USR_BLE = f"{BASE_URL}{AC}access_users/user/ble/activate"
DEACTIVATE_AC_USR_BLE = f"{BASE_URL}{AC}access_users/user/ble/deactivate"
SET_AC_USR_END_DATE = f"{BASE_URL}{AC}access_users/user/end_date"
REMOVE_AC_USR_ENTRY_CODE = f"{BASE_URL}{AC}access_users/user/entry_code"
SEND_APP_INVITE = f"{BASE_URL}{AC}access_users/user/pass/invite"
ACTIVATE_AC_USR_RU = f"{BASE_URL}{AC}access_users/user/remote_unlock/activate"
SET_AC_USR_START_DATE = f"{BASE_URL}{AC}access_users/user/start_date"
DELETE_AC_CARD = f"{BASE_URL}{AC}credentials/card"
ADD_CARD_TO_AC_USR = f"{BASE_URL}{AC}credentials/card"
ACTIVATE_AC_CARD = f"{BASE_URL}{AC}credentials/card/activate"
DEACTIVATE_AC_CARD = f"{BASE_URL}{AC}credentials/card/deactivate"
DELETE_AC_USR_PLATE = f"{BASE_URL}{AC}credentials/license_plate"
ADD_AC_USR_PLATE = f"{BASE_URL}{AC}credentials/license_plate"
ACTIVATE_AC_PLATE = f"{BASE_URL}{AC}credentials/license_plate/activate"
DEACTIVATE_AC_PLATE = f"{BASE_URL}{AC}credentials/license_plate/deactivate"
GET_DOOR_BY_ID = f"{BASE_URL}{AC}doors"
UNLOCK_AS_AC_USR = f"{BASE_URL}{AC}door/user_unlock"
UNLOCK_AS_AC_ADMIN = f"{BASE_URL}{AC}door/admin_unlock"
SET_AC_USR_ENTRY_CODE = (
    f"{BASE_URL}{AC}access_users/user/entry_code?override=false"
)
DEACTIVATE_AC_USR_RU = (
    f"{BASE_URL}{AC}access_users/user/remote_unlock/deactivate"
)

## Sensor API
GET_SENSOR_ALERTS = f"{BASE_URL}{SV}alerts"
GET_SENSOR_DATA = f"{BASE_URL}{SV}data"

## Guest API
GET_GUEST_SITES = f"{BASE_URL}{GUEST}sites"
GET_GUEST_VISITS = f"{BASE_URL}{GUEST}visits"

## Alarm API
GET_ALARM_DEVICES = f"{BASE_URL}{ALARM}devices"
GET_ALARM_SITE_INFO = f"{BASE_URL}{ALARM}sites"

## Events API
GET_EVENTS = f"{BASE_URL}{EVENT}access"

## Viewing Station API
GET_VX_DEVICES = f"{BASE_URL}{VX}devices"


##############################################################################
#############################  Custom Endpoints  #############################
##############################################################################


def set_org_id(org_id):
    """
    Returns the provided organization ID.

    Args:
        org_id: The organization ID to be set.

    Returns:
        The provided organization ID.
    """
    doorman = "https://vdoorman.command.verkada.com/"
    return {
        # * POST
        "DESK_DECOM": f"{ROOT}/organization/{org_id}/device/",
        "GUEST_IPADS_DECOM": f"{doorman}device/org/{org_id}/site/",
        "GUEST_PRINTER_DECOM": f"{doorman}printer/org/{org_id}/site/",
        "DESK_URL": f"{BASE_URL}vinter/v1/user/organization/{org_id}/device",
        "IPAD_URL": f"{doorman}site/settings/v2/org/{org_id}/site/",
        "ACCESS_LEVELS": f"https://vcerberus.command.verkada.com/organizations/{org_id}/schedules",
        # * DELETE
        "ACL_DECOM": f"https://vcerberus.command.verkada.com/organizations/{org_id}/schedules",
    }


def get_url(name, org_id):
    """
    Retrieves the URL associated with the provided name from the 'urls_with_org_id' dictionary.

    Args:
        name: The name used to retrieve the URL.
        org_id: The organization ID to be set.

    Returns:
        The URL associated with the provided name.
    """
    return set_org_id(org_id).get(name)


# Base Variables
ROOT = f"{BASE_URL}vinter/v1/user/async"
SHARD = "?sharding=true"

## Authentication
LOGIN = "https://vprovision.command.verkada.com/user/login"
LOGOUT = "https://vprovision.command.verkada.com/user/logout"

## Decom devices
# * POST
GET_ARCHIVE = "https://vsubmit.command.verkada.com/library/export/list"
DELETE_ARCHIVE = "https://vsubmit.command.verkada.com/library/export/delete"
APANEL_DECOM = "https://alarms.command.verkada.com/device/hub/decommission"
ASENSORS_DECOM = "https://alarms.command.verkada.com/device/sensor/delete"
CAMERA_DECOM = "https://vprovision.command.verkada.com/camera/decommission"

## Get devices
AC_URL = "https://vcerberus.command.verkada.com/get_entities"
ALARM_URL = "https://alarms.command.verkada.com/device/get_all"
VX_URL = "https://vvx.command.verkada.com/device/list"
GC_URL = "https://vnet.command.verkada.com/devices/list"
SV_URL = "https://vsensor.command.verkada.com/devices/list"
BZ_URL = "https://vbroadcast.command.verkada.com/management/speaker/list"

## Management
PROMOTE_ORG_ADMIN = (
    "https://vprovision.command.verkada.com/org/set_user_permissions"
)

# Misc
DASHBOARD_URL = "https://command.verkada.com/dashboard"
DEVICE_DATA = "https://vappinit.command.verkada.com/app/v2/init"
