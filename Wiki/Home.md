# Home

## API-Scripts

Welcome to the **API Scripts** Wiki! This repository is a private space where API scripts and projects are developed before being published to other repositories. Here you will find detailed documentation and resources to help you navigate and contribute to this repository.

### Overview

This repository is designed to:

- Enhance personal understand of how to work with APIs.
- Learn best practices when working with APIs.
- Stay up to date with coding skills by:
  - Continuously learning how to optimize code.
  - Experimenting with new methods of running code and making API calls.
- Create automation that may be shared with customers or used on customer organizations.

### Quick Start Guide

1. **Clone the Repository:**

    ```sh
    git clone https://github.com/ian-young/API_Scripts.git
    cd API_Scripts
    ```

2. **Checkout the Main Branch:**

    ```sh
    git checkout main
    ```

3. **Install Dependencies:**

    Make sure you have `Python` and `pip` installed. Then run:

    ```sh
    pip install -r requirements.txt
    ```

4. **Set up Environment Variables:**

    Download the [.env-generic](https://github.com/ian-young/API_Scripts/blob/main/.env-generic) file, rename it to `.env` and place it in the root directory of the project.

5. **Run a Script:**

    Execute the desired script by running:

    ```sh
    python your_script.py
    ```

### Table of Contents

1. [Home (Main Page)](https://github.com/ian-young/API_Scripts/blob/main/Wiki/Home.md)
    - Introduction
    - Quick Start Guide
    - Table of Contents
    - Branches
    - Projects
2. [Getting Started](https://github.com/ian-young/API_Scripts/blob/main/Wiki/Getting-Started.md)
    - Prerequisites
    - Installation
    - Configuration
    - Running the Project
3. [Usage](https://github.com/ian-young/API_Scripts/blob/main/Wiki/Usage.md)
    - Basic Usage
    - Advanced Usage
    - Examples
    - FaQ
4. [Development](https://github.com/ian-young/API_Scripts/blob/main/Wiki/Development.md)
    - Contributing Guidelines
    - Development Setup
    - Coding Standards
    - Testing
    - Building
    - Deployment
5. [Architecture](https://github.com/ian-young/API_Scripts/blob/main/Wiki/Architecture.md)
    - Overview
    - Modules
    - Data Flow
    - Design Decisions
6. [API Documentation](https://github.com/ian-young/API_Scripts/blob/main/Wiki/API-Documentation.md)
    - REST API
    - GraphQL API
    - SDKs and Libraries
7. [Troubleshooting](https://github.com/ian-young/API_Scripts/blob/main/Wiki/Troubleshooting.md)
    - Common Issues
    - Debugging
    - Error Codes
8. [Release Notes](https://github.com/ian-young/API_Scripts/blob/main/Wiki/Release-Notes.md)
    - Changelog
    - Upgrade Guide
9. [Resources](https://github.com/ian-young/API_Scripts/blob/main/Wiki/Resources.md)
    - External Links
    - Community
    - License
10. [Contact](https://github.com/ian-young/API_Scripts/blob/main/Wiki/Contact.md)
    - Maintainers
    - Support

### Branches

The repository consists of three main branches:

1. The [main](https://github.com/ian-young/API_Scripts)
    - Contains working, production-level code.
    - Scripts in this branch are ready to be shared, as credentials are not hard-coded.
    - Make sure to use the [requirements.txt](https://github.com/ian-young/API_Scripts/blob/main/requirements.txt) and [.env-generic](https://github.com/ian-young/API_Scripts/blob/main/.evn-generic) files when getting started with scripts from this repository. Remember to rename `.env-generic` to `.env` and that it is located in the same directory as the script being ran for proper functionality. Alternatively, the [.env-template](https://github.com/ian-young/API_Scripts/blob/main/.env-template) may also be used if running with multiple Verkada organizations.
2. The [wip](https://github.com/ian-young/API_Scripts/tree/wip) (Work In Progress)
    - Contains code that is working but still under development or debugging.
3. Private repository
    - There is a private repository where all files are originally created, developed and tested before being released to the public.
    - Assures security and safety of the code during the development process.
    - Only highly experimental code stays private without being released to the public

>[!TIP]
>Development should start at the lowest branch (ideas) and progress to the production branch (main).

### Projects

Scripts with significant impact will have an associated project where issues can be posted and organized. These projects help in the structured development of scripts and can include:

- Bug reports
- Documentation requests
- Feature requests

#### Current Projects

At present, the repository is caught up and no active projects are running.
