# Getting Started

## Prerequisites

Before you begin, ensure you have the following software installed on your terminal:

1. **Python**
    - Download and install Python from the [official Python website](https://www.python.org/downloads/).
        - If using Windows, use [this link](https://www.python.org/downloads/windows/) to download Python from their official website or navigate to the Microsoft Store and download Python from there.
        - If using a flavor of Ubuntu ,run the following command in your terminal:

        ```sh
        sudo apt update
        sudo apt install python3
        ```

        - If using a flavor of Debian, run the following command in your terminal:

        ```sh
        sudo dnf install python3
        ```

        - If using Mac, run the following commands in your terminal:
            1. Install [Homebrew](https://brew.sh/)

                ```sh
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                ```

            2. Install Python

                ```sh
                brew install python3
                ```

2. **pip** (Python package Installer)
    - pip is included with Python. To verify:

        ```sh
        pip --version
        ```

3. **Git**
    - Download and install Git from the [official Git website](https://git-scm.com/downloads).
        - If using Windows, use [this link](https://git-scm.com/download/win) to download Git from their official website.
        - If using a flavor of Ubuntu ,run the following command in your terminal:

            ```sh
            sudo apt update
            sudo apt install git
            ```

        - If using a flavor of Debian, run the following command in your terminal:

            ```sh
            sudo dnf install git
            ```

        - If using Mac, run the following commands in your terminal:
            1. Install [Homebrew](https://brew.sh/)

                ```sh
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                ```

            2. Install Python

                ```sh
                brew install git
                ```

    - Verify the installation:

        ```sh
        git --version
        ```

4. **Docker**
    - Download and install Docker from the [official Docker website](https://www.docker.com/products/docker-desktop/).
    - Follow the installation instructions for your operating system.
    - Verify the installation:

        ```fish
        docker --version
        docker-compose --version
        ```

## Installation

### 1. Clone the Repository

Open your terminal or command prompt and run:

```sh
git clone https://github.com/ian-young/API_Scripts.git
cd API_Scripts
```

### 2. Checkout the Main Branch

Switch to the `main` branch, which contains the production-level code:

```sh
git checkout main
```

### 3. Create and Activate a Python Virtual Environment

It is recommended to use a virtual environment to manage dependencies. Here's how to create activate one:

1. **Create a virtual environment**:

    ```sh
    python -m venv env
    ```

2. **Activate the virtual environment**:
    - On Windows:

        ```powershell
        ./env/Scripts/activate
        ```

    - On macOS and Liunx:

        ```sh
        source env/bin/activate
        ```

### 4. Install Dependencies

With the virtual environment activated, install the required dependencies:

```sh
pip install -r requirements.txt
```

## Configuration

### .env File Setup

The project uses environment variables for configuration, managed by the python-dotenv module. Follow these steps to configure your environment variables:

1. **Download the .env-generic File**:
    Download the [.env-generic](https://github.com/ian-young/API_Scripts/blob/main/.env-generic) file.

2. **Rename and Move the File**:
    Rename the file to .env and move it to the root directory of the project:

    ```sh
    mv .env-generic .env
    ```

3. **Edit the .env File**:
Open the `.env` file in a text editor and fill in the necessary environment variables. Ensure this file is in the same directory as your script or located in the root directory of the project for it to function properly.

## Running the Project

### Running Python Scripts

With everything set up, you can now run your scripts. For example:

```sh
python your_script.py
```

>[!IMPORTANT]
>Ensure your virtual environment is activated each time you work with the project to manage dependencies correctly.

### Running the Docker Application

if your project includes the Docker application, follow these steps:

1. **Build and Compose the Docker Containers**:

    ```fish
    docker-compose up --build
    ```

2. **Start the Docker Containers**:

    ```fish
    docker-compose up
    ```

3. **Access the Application**:
    - Open the web browser and navigate to `http://localhost`
    - The Nginx server is configured to block all other traffic, ensuring only your local machine can access it.

> [!NOTE]
> To stop the Docker containers, use the command `docker-compose down`. If you make changes and need to rebuild the Docker containers, use `docker-compose up --build`.
