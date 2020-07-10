""" Utility routines for handling control file contents."""

def cfg_string_to_list(input_string):
    """ Convert a string containing items separated by commas into a list."""
    input_string = "".join(input_string.split())
    if "," in input_string:
        output_list = input_string.split(",")
    else:
        output_list = [input_string]
    return output_list