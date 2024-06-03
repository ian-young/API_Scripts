# Architecture

## Overview

The **API Scripts** repository is designed to provide a structured and scalable way to manage API scripts and projects. The architecture is modular, ensuring each component can be developed, tested, and deployed independently. The high-level architecture includes the following components:

- **Scripts**: Individual Python scripts that interact with various APIs.
- **Docker Containers**: Encapsulated environments for running specific applications or services.
- **Virtual Environment**: Isolated Python environment for dependency management.
- **Configuration Management**: Using environment variables to manage configuration settings securely.

## Modules

### Detailed Descriptions of Each Module/Component

1. **Scripts Module**:
    - **Description**: This module contains all the Python scripts that interact with different APIs. Each script is designed to perform specific tasks such as data retrieval, processing, or automation.
    - **Key Files**:

        - **[command_action_template.py](https://github.com/ian-young/API_Scripts/blob/main/command_action_template.py)**: A template script demonstrating API interaction and how to authenticate to Verkada Command to preform user actions.

        - **[.env](https://github.com/ian-young/API_Scripts/blob/main/.env-generic)**: The file that stores API credentials, voiding the need to have exposed credentials in the scripts.

        - **Dependencies**: Managed through [requirements.txt](https://github.com/ian-young/API_Scripts/blob/main/requirements.txt).

2. **Docker Module**:
    - **Description**: This module encapsulates certain applications or services into Docker containers, ensuring consistent environments across different setups.
    - **Key Files**:
        - [Dockerfile](https://github.com/ian-young/API_Scripts/blob/main/Try_Endpoints/Dockerfile): Instructions to build the Docker image.
        - [docker-compose.yml](https://github.com/ian-young/API_Scripts/blob/main/Try_Endpoints/docker-compose.yml): Configuration for Docker Compose to manage multi-container applications.
    - **Components**:
        - **Nginx Container**: Acts as a reverse proxy server.
        - **Application Container**: Runs the core application/service.

3. **Configuration Module**:
    - **Description**: Manages configuration settings using environment variables.
        - **Key Files**:
            - [.env-generic](https://github.com/ian-young/API_Scripts/blob/main/.env-generic): Template file for environment variables.
            - `.env`: Actual configuration file used by the application (created from .env-generic).

4. Virtual Environment Module:
    - **Description**: Provides an isolated Python environment to manage dependencies and avoid conflicts.
        - Setup:
            - Created using `python -m venv env`.
            - Activated in the terminal before running scripts.

## Data Flow

### How Data Flows Through the System

1. **User Input**:
    - The user triggers a script or a Docker application by executing a command in the terminal.

2. **Environment Configuration**:
    - The system loads configuration settings from the `.env` file.

3. **API Interaction**:
    - Scripts send requests to external APIs using the configurations and credentials from the `.env` file.
    - Responses from the APIs are processed and stored or utilized as needed.

4. Data Processing:
    - Scripts may process the data retrieved from APIs, performing tasks like data cleaning, transformation, or analysis.

5. Output:
    - Processed data is either outputted to the console, saved to a file, or sent to another service/API.

6. Docker Application:
    - If using Docker, the application runs inside a container, managing incoming HTTP requests, processing them, and returning responses.

## Design Decisions

### Key Design Decisions and Their Rationales

1. Modular Architecture:
    - **Rationale**: Ensures each component can be developed, tested, and maintained independently, promoting code re-usability and scalability.

2. **Environment Variables for Configuration**:
    - **Rationale**: Keeps sensitive information like API keys and passwords out of the source code, enhancing security and flexibility.

3. **Use of Docker**:
    - **Rationale**: Provides a consistent environment across different machines, simplifying deployment and reducing the "it works on my machine" problem.

4. **Virtual Environment for Python Dependencies**:
    - **Rationale**: Prevents dependency conflicts by isolating project-specific dependencies from the system-wide Python environment.

5. **Adoption of PEP 8 Style Guide**:
    - **Rationale**: Ensures code readability and maintainability by following a widely accepted Python coding standard.
