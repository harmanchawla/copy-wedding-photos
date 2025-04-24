import os
import shutil
from typing import List
from pydantic import BaseModel, FilePath, DirectoryPath, ValidationError


class InputData(BaseModel):
    file_list_path: FilePath
    input_dir: DirectoryPath
    output_dir: str  # Allow non-existent directories, validate later


def validate_inputs(file_list_path: str, input_dir: str, output_dir: str) -> InputData:
    """
    Validate the inputs using Pydantic.
    """
    try:
        data = InputData(
            file_list_path=file_list_path,
            input_dir=input_dir,
            output_dir=output_dir,
        )
        # Ensure the output directory is valid (can be created if it doesn't exist)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        elif not os.path.isdir(output_dir):
            raise ValueError(f"Output path '{output_dir}' exists but is not a directory.")
        return data
    except ValidationError as e:
        print(f"Input validation error:\n{e}")
        exit(1)
    except Exception as e:
        print(f"Error validating inputs: {e}")
        exit(1)


def read_file_list(file_list_path: str) -> List[str]:
    """
    Read the list of file names from the provided file.
    """
    try:
        with open(file_list_path, 'r') as file:
            return [line.strip() for line in file.readlines()]
    except Exception as e:
        print(f"Error reading file list '{file_list_path}': {e}")
        exit(1)


def find_file(file_name: str, directory: str) -> str:
    """
    Recursively search for a file in the directory.
    """
    for root, _, files in os.walk(directory):
        if file_name in files:
            return os.path.join(root, file_name)
    return None


def copy_files(file_list: List[str], input_dir: str, output_dir: str):
    """
    Copy files from the input directory to the output directory.
    """
    for file_name in file_list:
        print(f"Searching for file: {file_name}")
        try:
            file_path = find_file(file_name, input_dir)
        except Exception as e:
            print(f"Error searching for file '{file_name}': {e}")
            continue

        if file_path:
            print(f"File found: {file_name}")
            try:
                shutil.copy(file_path, output_dir)
                print(f"File copied: {file_name}")
            except Exception as e:
                print(f"Error copying file '{file_name}': {e}")
        else:
            print(f"File not found: {file_name}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Copy files from an input directory to an output directory.")
    parser.add_argument("file_list_path", help="Path to the file containing the list of file names.")
    parser.add_argument("input_dir", help="Path to the input directory.")
    parser.add_argument("output_dir", help="Path to the output directory.")

    args = parser.parse_args()

    # Validate inputs
    validated_data = validate_inputs(args.file_list_path, args.input_dir, args.output_dir)

    # Read the file list
    file_list = read_file_list(validated_data.file_list_path)

    # Copy files
    copy_files(file_list, validated_data.input_dir, validated_data.output_dir)
