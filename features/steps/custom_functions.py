from behave import given
from os import path
import csv

def load_data_from_csv(file_path):
    """Loads data from a CSV file into a list of lists.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        list[list]: A list of lists representing the loaded data.
    """
    file_path = path.realpath(path.join(path.dirname(__file__), '..', 'custom', file_path))

    try:
        with open(file_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            data = list(reader)
            return data
    except FileNotFoundError:
        raise Exception(f"Error: File not found: {file_path}")
        return None

def convert_to_hyphen_case(string):
    """Converts a string to hyphen case.

    Args:
        string (str): The input string.

    Returns:
        str: The string in hyphen case.
    """

    words = string.split()
    hyphenated_words = "-".join(word.lower() for word in words)
    return hyphenated_words

@given('we load examples from "{file_name}"')
def given_load_data_from_csv(context, file_name):
    """Given step that loads data from a CSV file into context.table.

    Args:
        context (object): The Behave context object.
        file_name (str): The name of the CSV file (without the .csv extension).
    """

    file_path = f"{context.domain}/{convert_to_hyphen_case(file_name)}.csv"
    data = load_data_from_csv(file_path)

    print(data)
    print("loaded from " + file_path)

    if data is not None:
        context.loaded_table = data[1:]