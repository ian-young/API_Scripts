# Usage

This section provides detailed instructions on how to use the scripts in the **API Scripts** repository.

## Basic Usage

### Running Python Scripts

1. **Ensure the .env file is configured**:
    - Follow the instructions in the [Getting Started](https://github.com/ian-young/API_Scripts/blob/main/Wiki/Getting-Started.md) section to set up your `.env` file.
2. **Activate the Virtual Environment**:
    - On Windows:

    ```Powershell
    ./env/Scripts/activate
    ```

    - On macOS and Linux

    ```sh
    source env/bin/activate
    ```

3. **Run the Desired Script**:

    ```sh
    python example_script.py
    ```

## Advanced Usage

### Using the Docker Application

The repository includes a Docker application consisting of two containers. Follow these steps to build, compose, and run the Docker containers:

1. **Build and Compose the docker Containers**:

    ```fish
    docker-compose up --build
    ```

2. **Start the Docker Containers**:

    ```sh
    docker-compose up
    ```

3. **Access the Application**:
    - Open your web browser and navigate to `localhost`
    - The Nginx server is configured to block all other traffic, ensuring only your local machine can access it.

## Example Commands

- **To stop the Docker containers**:

    ```sh
    docker-compose down
    ```

- **To rebuild the Docker containers after making changes**:

    ```fish
    docker-compose up --build
    ```

## Important Notes

- **Environment Configuration**:

    Ensure your `.env` file is correctly configured and placed in the same directory as your scripts.

- **Directory Structure**:

    Keep all scripts in the same directory to avoid issues with interdependent scripts.

## Common Tasks and Workflows

- **Updating Dependencies**:

    If you need to update the Python dependencies, modify the `requirements.txt` file and run:

    ```fish
    pip install -r requirements.txt --upgrade
    ```

## FAQ

1. **Why is my script not running?**
    - Ensure the virtual environment is activated.
    - Verify the `.env` file is correctly configured and placed in the root directory.
2. **How do I access the Docker application?**
    - Open your web browser and navigate to `http://localhost` once the containers are running
3. **What if I need to stop the Docker application?**
    - Use the command:

        ```sh
        docker-compose down
        ```
