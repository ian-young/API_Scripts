"""Streamline imports"""

import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

import requests

from .authentication import login_and_get_tokens, logout
from .custom_exceptions import APIExceptionHandler, APIThrottleException
from .log import log
from .rate_limit import run_thread_with_rate_limit
from .verkada_totp import generate_totp


@dataclass
class SharedParams:
    """
    Data class that holds shared parameters for device deletion
    operations.

    This class encapsulates the common parameters required for performing
    deletion requests in the Verkada API. It provides a structured way to
    manage the authentication and session information needed for the
    operations.

    Attributes:
        delete_session (requests.Session): The session used for making the
            API calls.
        x_verkada_token (str): The CSRF token for a valid, authenticated
            session.
        x_verkada_auth (str): The authenticated user token for a valid
            Verkada session.
        usr (str): The user ID of the authenticated user for a valid Verkada
            Command session.
        org_id (Optional[str]): The organization ID for the targeted Verkada
            organization.
    """

    session: requests.Session
    x_verkada_token: str
    x_verkada_auth: str
    usr: str
    org_id: Optional[str]


class ResultThread(threading.Thread):
    """
    A subclass of threading's Thread. Creates a new thread where the return
    values are saved to be viewed for later. They may be accessed by typing
    the objectname.result
    """

    def __init__(self, target, *args, **kwargs):
        super().__init__(target=target, args=args, kwargs=kwargs)
        self._result = None

    def run(self):
        self._result = self._target(*self._args, **self._kwargs)

    @property
    def result(self) -> Any:
        """
        Passes back the return value of the function ran.
        """
        return self._result


# Define a helper function to create threads with arguments
def create_thread_with_args(target: Callable, args: Any) -> ResultThread:
    """
    Allows the creation of a ResultThread and still pass arguments to the
    thread.

    :param target: The function that the thread will be running.
    :type target: function
    :param args: The arguments that will be passed through the function.
    :type args: Any
    :return: Returns a ResultThread
    :rtype: thread
    """
    return ResultThread(target=lambda: target(*args))
