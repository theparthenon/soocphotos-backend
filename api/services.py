"""Contains functions to start and stop services."""

import subprocess
import time

import requests

from api.utils import logger

# Define all the services that can be started, with their respective ports
SERVICES = {
    "image_similarity": 8002,
    "thumbnail": 8003,
    "face_recognition": 8005,
    "llm": 8008,
    "image_captioning": 8007,
    "exif": 8010,
    "tags": 8011,
}


def check_services():
    """Checks the health of all services. If any service is not healthy,
    it will be stopped and restarted."""

    for service in SERVICES.keys():  # pylint: disable=consider-iterating-dictionary
        if not is_healthy(service):
            stop_service(service)
            logger.info("Restarting %s", service)
            start_service(service)


def is_healthy(service):
    """
    Checks the health of a given service.
    Parameters:
        service (str): The name of the service to check.
    Returns:
        bool: True if the service is healthy, False otherwise.
    Raises:
        OSError: If there is an error checking the health of the service.
                 This function sends a GET request to the service's health endpoint
                 (`http://localhost:{port}/health`) and checks the response status code.
                 If the response has a "last_request_time" field, it also checks if the
                 service is stale (more than 120 seconds since the last request) and needs
                 to be restarted. If there is an error checking the health of the service,
                 an OSError is raised.
    """

    port = SERVICES.get(service)
    try:
        res = requests.get(f"http://localhost:{port}/health", timeout=120)
        # If response has timestamp, check if it needs to be restarted
        if res.json().get("last_request_time") is not None:
            if res.json()["last_request_time"] < time.time() - 120:
                logger.info("Service %s is stale and needs to be restarted", service)
                return False
        return res.status_code == 200
    except OSError as e:
        logger.exception("Error checking health of %s: %s", service, str(e))
        return False


def start_service(service):
    """
    A function to start a service based on the provided service name.

    Parameters:
        service (str): The name of the service to start.

    Returns:
        bool: True if the service started successfully, False otherwise.
    """

    if service in SERVICES.keys():  # pylint: disable=consider-iterating-dictionary
        subprocess.Popen(
            [
                "python",
                f"service/{service}/main.py",
                "2>&1 | tee {settings.BASE_LOGS}/{service}.log",
            ]
        )
    else:
        logger.warning("Unknown service: %s", service)
        return False

    logger.info("Service '%s' started successfully", service)
    return True


def stop_service(service):
    """
    Stops the specified service by finding its process ID (PID) using `ps` and `grep`,
    and then killing each process found.
    Parameters:
        service (str): The name of the service to stop.
    Returns:
        bool: True if the service was stopped successfully, False otherwise.
    """

    try:
        # Find the process ID (PID) of the service using `ps` and `grep`
        ps_command = f"ps aux | grep '[p]ython.*{service}/main.py' | awk '{{print $2}}'"
        result = subprocess.run(
            ps_command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        pids = result.stdout.decode().strip().split()

        if not pids:
            logger.warning("Service '%s' is not running", service)
            return False

        # Kill each process found
        for pid in pids:
            subprocess.run(["kill", "-9", pid], check=True)
            logger.info("Service '%s' with PID %d stopped successfully", service, pid)

        return True
    except subprocess.CalledProcessError as e:
        logger.error(
            "Failed to stop service '%s': %s", service, e.stderr.decode().strip()
        )
        return False
    except OSError as e:
        logger.error("An error occurred while stopping service '%s': %s", service, e)
        return False
