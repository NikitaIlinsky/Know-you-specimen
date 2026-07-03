import os
from typing import List


def get_image_paths(image_dir, allowed_extensions) -> List[str]:
    """
    Returns a list of file paths from the configured input directory
    that match the allowed extensions defined in the configuration.

    Returns:
        List[str]: A list of file paths that match the allowed extensions
    """

    # Check if the directory exists
    if not os.path.exists(image_dir):
        print(f"Warning: Input directory '{image_dir}' does not exist.")
        return []

    # Get all files in the directory
    all_files = os.listdir(image_dir)

    # Filter files based on allowed extensions
    filtered_files = []
    for file in all_files:
        file_ext = os.path.splitext(file)[1].lower()
        if file_ext in allowed_extensions:
            file_path = os.path.join(image_dir, file)
            if os.path.isfile(file_path):  # Ensure it's a file, not a subdirectory
                filtered_files.append(file_path)

    return filtered_files
