# Development

## Contributing Guidelines

### How to Contribute to the Project

We welcome contributions to the **API Scripts** repository. To contribute:

1. **Fork the Repository**:
    - Navigate to the [Command APIs repository](https://github.com/ian-young/API_Scripts).
    - Click the "Fork" button in the upper right corner.

2. **Clone Your Fork**:

    ```sh
    git clone https://github.com/ian-young/API_Scripts.git
    cd API_Scripts
    ```

3. **Create a Branch**:

    ```sh
    git checkout -b feature/your-feature-name
    ```

4. **Make Your Changes**:
    - Implement your feature or bug fix.

5. **Commit Your Changes**:

    ```sh
    git add .
    git commit -m "Add a descriptive commit message"
    ```

6. **Push Your Branch**:

    ```sh
    git push origin feature/your-feature-name
    ```

7. **Create a Pull Request**:
    - Navigate to your forked repository on GitHub.
    - Click the "Compare & pull request" button.
    - Submit your pull request for review.

### Code of Conduct

We adhere to the Contributor Covenant Code of Conduct. By participating, you are expected to uphold this code. Please report any unacceptable behavior to the repository maintainers.

## Development Setup

### Setting Up a Local Development Environment

1. **Clone the Repository**:

    ```sh
    git clone https://github.com/ian-young/API_Scripts.git
    cd API_Scripts
    ```

2. **Checkout the Development Branch**:

    ```sh
    git checkout wip
    ```

3. **Create and Activate a Virtual Environment**:

    ```sh
    python -m venv env
    source env/bin/activate  # On Windows use `.\env\Scripts\activate`
    ```

4. **Install Dependencies**:

    ```sh
    pip install -r requirements.txt
    ```

### Tools and Configurations for Developers

- **Code Editor**: We recommend using [Visual Studio Code](https://code.visualstudio.com/).
- **Linters and Formatters**: Ensure you have linters and formatters configured in your editor, such as pylint and black.
- **Version Control**: Use Git for version control. Make sure to configure your Git settings (username, email).

## Coding Standards

### Style Guides and Best Practices

- **PEP 8**: Follow the PEP 8 style guide for Python code.
  - Please keep lines *79 characters* or less including white-space.
- **Docstrings**: Use proper docstrings for documenting modules, classes, and functions.
- **Comments**: Write clear and concise comments where necessary.

Example:

```python

def example_function(param1, param2):
    """
    This is an example function.

    Args:
        param1 (int): The first parameter.
        param2 (int): The second parameter.

    Returns: The sum of param1 and param2.
    rtype: int
    """
    return param1 + param2  # Add the two parameters together
```

## Testing

### Running Tests and Testing Strategies

1. **Install Testing Dependencies**:
    - Ensure pytest or any other testing framework used is listed in requirements.
    - Fork the branch that you intend to test on.

2. **Run Tests**:

    ```sh
    pytest tests/
    ```

3. **Writing Tests**:
    - Place your test files in a `tests` directory.
    - Use descriptive test case names.

        Example test file structure:

        ```markdown
        tests/
            test_example.py
        ```

        Example test case:

        ```python
        def test_example_function():
            assert example_function(1, 2) == 3
        ```

## Building

### Build Instructions and Scripts

If there are any build steps required, outline them here. For instance, if building a Docker image:

```sh
docker build -t API_Scripts:latest .
```

Include any build scripts or Makefiles if applicable.

## Deployment

### Deployment Steps and Environment Details

1. **Prepare the Environment**:
    - Ensure all environment variables are set up as per the .env file.

2. **Deploy Using Docker**:

    ```fish
    docker-compose up --build -d
    ```

3. **Verify Deployment**:
    - Check the running containers:

        ```sh
        docker ps
        ```

    - Access the application via `http://localhost`.

4. **Stopping the Application**:

    ```sh
    docker-compose down
    ```
