"""
Author: Ian Young
Co-Author: ChatGPT
Purpose: Pad and center given input with `#` to meet 79 characters.
"""
def format_string(input_string):
    """
    Centers the input string within a total width of 79 characters by adding padding and whitespace.
    
    Args:
        input_string (str): The string to be centered within the total width.
    
    Returns:
        None
    """
    # Total width of the string including padding and whitespace
    total_width = 78
    # Create the top and bottom border
    border = "#" * total_width

    # Calculate padding needed
    padding_length = (total_width - len(input_string) - 8) // 2
    # Create the centered line with '#' padding
    centered_string = '#' * padding_length + '  ' + input_string + '  ' + '#' * padding_length

    # Adjust if the total length is not exactly 79 characters
    if len(centered_string) < total_width - 4:
        centered_string += '#'

    # Format the middle line with '#' on the sides
    formatted_string = f"##{centered_string}##"

    # Print the formatted output
    print(border)
    print(formatted_string)
    print(border)

# Example usage
format_string(str(input("Divider title: ")))
