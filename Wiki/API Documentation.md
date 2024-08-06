# API Documentation

## REST API

### Overview

This section provides detailed documentation on how to interact with the public REST API provided by Verkada. The API allows you to manage persons of interest, retrieve data, and perform other operations.

### Endpoint Descriptions

For a comprehensive list of endpoints, please refer to the [Verkada API Documentation](https://apidocs.verkada.com/).

### Request and Response Formats

#### GET Request Example

Retrieve a list of persons of interest in your organization.

```python
import requests

url = "https://api.verkada.com/cameras/v1/people/person_of_interest?page_size=100"

headers = {
    "accept": "application/json",
    "x-api-key": "your-api-key"
}

response = requests.get(url, headers=headers)

print(response.text)
```

#### POST Request Example

Add a new person of interest to your organization.

```python
import requests

url = "https://api.verkada.com/cameras/v1/people/person_of_interest"

payload = {
    "base64_image": "base64-image-string",
    "label": "name/label of PoI"
}
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-api-key": "your-api-key"
}

response = requests.post(url, json=payload, headers=headers)

print(response.text)
```

#### PATCH Request Example

Update an existing person of interest's label.

```python
import requests

url = "https://api.verkada.com/cameras/v1/people/person_of_interest?person_id=person-id"

payload = { "label": "name/label of PoI" }
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-api-key": "your-api-key"
}

response = requests.patch(url, json=payload, headers=headers)

print(response.text)
```

#### DELETE Request Example

Delete a person of interest from your organization.

```python
import requests

url = "https://api.verkada.com/cameras/v1/people/person_of_interest?person_id=person-id"

headers = {
    "accept": "application/json",
    "x-api-key": "your-api-key"
}

response = requests.delete(url, headers=headers)

print(response.text)
```

### Authentication and Authorization

#### API Key Authentication

To interact with the Verkada API, you must include your API key in the request headers.

- **Headers**:

```json
{
    "accept": "application/json",
    "x-api-key": "YOUR_API_KEY"
}
```

#### Emulating User Actions

For actions that require emulating user behavior, you need to authenticate using user credentials to obtain a session token.

1. **Login**:
    - **Endpoint**: <https://vprovision.command.verkada.com/user/login>
    - **Method**: `POST`
    - **Headers**: None
    - **Body**:

    ```json
    {
        "email": "username",
        "password": "password",
        "org_id": "org_id"
    }
    ```

    - **Response**:

    ```json
    {
      "x-verkada-token": "YOUR_SESSION_TOKEN"
    }
    ```

2. **Headers for User Actions**:

    ```json
    {
        "x-verkada-token": "YOUR_SESSION_TOKEN",
        "x-verkada-organization-id": "YOUR_ORG_ID"
    }
    ```

3. **Logout**:

    - **Endpoint**: <https://vprovision.command.verkada.com/user/logout>
    - **Method**: `POST`
    - **Headers**:

    ```json
    {
        "x-verkada-token": "YOUR_SESSION_TOKEN"
    }
    ```

### Example Script

Here’s [an example script](https://github.com/ian-young/API_Scripts/blob/main/Demo_Org/auto_reset_interests.py) demonstrating the use of the Verkada public REST API to manage persons of interest.

## Docker Application

### Purpose

The Docker application pings all public endpoints and graphs their server load and failure rate over a 24-hour period using Matplotlib. The graphs are presented in UTC.

### Accessing the Docker Application

1. **Build and Run Instructions**:
    - Detailed instructions can be found on the [Getting Started](https://github.com/ian-young/API_Scripts/blob/main/Wiki/Getting-Started.md) page.

2. **Accessing the Application**:
    - Open your web browser and navigate to `http://localhost`.
    - The application uses Matplotlib to plot the server load and failure rate.

- **Server Load**: Server load is determined by how many 429 errors are returned by the endpoints as stated by the [AWS throttling page](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_usage_plan#throttling-settings-arguments).
- **Failure Rate**: Failure is measured by how many 500 and 404 error codes are sent back each wave.
