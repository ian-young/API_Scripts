# Troubleshooting

## Common Issues

### Issue: Authentication Failure

**Description**: Users encounter authentication errors when trying to access certain endpoints or perform operations.

**Solution**: Ensure that the API key and organization ID are correctly included in the request headers. Double-check for any typos or formatting errors. Double-check API key permissions.

### Issue: Rate Limit Exceeded

**Description**: Users receive HTTP 429 Too Many Requests errors, indicating that they have exceeded the rate limit for API calls. The API rate limit may vary from 5-20 calls per second depending on server load. 5 calls per second will more consistently avoid a 429 error, 10 is the happy mix between speed and avoiding a 429 error. Verkada recommends 5 calls per second in the [API documentation](https://apidocs.verkada.com/reference/ratelimiting).

**Solution**: Implement rate limiting on your end to avoid exceeding the API's rate limits. Consider optimizing your code to minimize unnecessary API calls.

### Issue: Missing Data

**Description**: Users do not receive the expected data or encounter missing fields in the API responses.

**Solution**: Check the documentation for the specific endpoint to ensure that you are providing all required parameters and properly parsing the response data. If certain fields are optional, handle cases where they may be missing gracefully in your code.

## Debugging

## Tips for Debugging API Requests

1. **Logging**: Utilize logging libraries to output debug messages, including request parameters, headers, and response data.
2. **Code Reviews**: Collaborate with team members to review code and identify potential issues or areas for improvement.
3. **Testing**: Write unit tests for your API integration code to verify its functionality and catch any regressions.

### Tools for Debugging

- [**API Documents**](https://apidocs.verkada.com/reference/introduction): Verkada API docs have working code that has plug and play functionality. Once the code is working in the language of your choice in the documents, copy and paste it into your script.
- **`curl`**: Command-line tool for making HTTP requests, useful for quick debugging and testing.
- **Web Browser DevTools**: Inspect network requests in the browser's developer tools to troubleshoot client-side API interactions.

## Error Codes

### 400 Bad Request

**Description**: The server cannot process the request due to a client error, such as invalid input data or missing parameters.

**Solution**: Review the request parameters and ensure that they conform to the API's specifications. Verify that all required fields are included and correctly formatted.

### 401 Unauthorized

**Description**: Authentication is required to access the requested resource, but the user credentials provided are invalid, expired, or missing.

**Solution**: Double-check the API key and organization ID used in the request headers. If using user authentication, ensure that the user has the necessary permissions to access the resource.

### 429 Too Many Requests

**Description**: The client has exceeded the rate limit for API calls, and the server is temporarily unable to process additional requests.

**Solution**: Implement rate limiting on the client side to prevent exceeding the API's rate limits. Consider using exponential backoff or other strategies for retrying failed requests.

### 404 Not Found

**Description**: The client requests data from an endpoint and the server cannot find where to send it to.

**Solution**: Double-check the endpoint URL for any typos and making sure that the correct endpoint is being targeted with an approved/accepted HTTP request option.

### 500 Internal Server Error

**Description**: The client requests data from the endpoint and the endpoint fails to process the query in the backend.

**Solution**: Give the endpoint some time, they will timeout and return a 500 if the global queue is too large. If it is still returning with a 500 after 5 minutes or so, reach out to the Verkada Support team.
