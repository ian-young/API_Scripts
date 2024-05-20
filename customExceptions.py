# Author: Ian Young
# Purpose: Import into other files to use custom expections and save space.

import requests
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)  # Initialize colorized output


class APIThrottleException(Exception):
    """
    Exception raised when the API request rate limit is exceeded.

    :param message: A human-readable description of the exception.
    :type message: str
    """

    def __init__(self, message="API throttle limit exceeded."):
        self.message = message
        super().__init__(self.message)


class APIExceptionHandler(Exception):
    """
    Exception handler for various requests exceptions.

    :param exception: The exception to be handled.
    :type exception: Exception
    :param response: The response object, if available.
    :type response: requests.Response
    :param service_name: The name of the service or endpoint.
    :type service_name: str
    """

    def __init__(self, exception, response=None, service_name="Service"):
        self.exception = exception
        self.response = response
        self.service_name = service_name
        self.handle_exception()

    def handle_exception(self):
        if isinstance(self.exception, requests.exceptions.Timeout):
            self.message = f"{Fore.RED}Connection timed out.{Style.RESET_ALL}"
        elif isinstance(self.exception, requests.exceptions.TooManyRedirects):
            self.message = (f"{Fore.RED}Too many redirects. Aborting..."
                            f"{Style.RESET_ALL}")
        elif isinstance(self.exception, requests.exceptions.HTTPError):
            if self.response is not None:
                self.message = (
                    f"{Fore.RED}{self.service_name} "
                    f"returned with a non-200 code: "
                    f"{self.response.status_code}{Style.RESET_ALL}"
                )
            else:
                self.message = (
                    f"{Fore.RED}HTTP error occurred.{Style.RESET_ALL}"
                )
        elif isinstance(self.exception, requests.exceptions.ConnectionError):
            self.message = (f"{Fore.RED}Error connecting to the server."
                            f"{Style.RESET_ALL}")
        elif isinstance(self.exception, requests.exceptions.RequestException):
            self.message = (f"{Fore.RED}Verkada API Error:{Style.RESET_ALL} "
                            f"{self.exception}")
        else:
            self.message = (
                f"{Fore.RED}An unknown error occurred.{Style.RESET_ALL}"
            )

        super().__init__(self.message)
