# QoL

These are scripts that may be utilized to improve the coding experience within this repository.

## Formatting

### [create_code_divider.py](https://github.com/ian-young/API_Scripts/blob/main/QoL/create_code_divider.py)

This script may be run to output a given string padded with the `#` character to center it. The divider will not exceed 79 characters to adhere to PEP8 standards.

## Module Importing

### [custom_exceptions.py](https://github.com/ian-young/API_Scripts/blob/main/QoL/custom_exceptions.py)

This file houses all custom exceptions that are used throughout the rest of the scripts to help shorten file size and standardize output.

### [avl_tree.py](https://github.com/ian-young/API_Scripts/blob/main/QoL/avl_tree.py)

Can build, manage, delete, compare and manipulate AVL trees to reduce Big O runtime in scripts that handle large files and need to make lots of search calls, compares and/or node modifications.

### [api_endpoints.py](https://github.com/ian-young/API_Scripts/blob/main/QoL/api_endpoints.py)

Contains a list of all known and used endpoints. The reason for importing this script is to help reduce the amount of lines used in a single file and prevent any potential typos when writing out or using long URLs.

### [verkada_totp.py](https://github.com/ian-young/API_Scripts/blob/main/QoL/verkada_totp.py)

Can serve as a 2FA method and will aid with the secure authentication into Command.
