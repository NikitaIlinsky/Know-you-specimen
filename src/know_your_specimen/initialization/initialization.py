import os
from typing import List


def get_image_paths(image_dir: str, allowed_extensions: set) -> List[str]:
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

    if not filtered_files:
        print(f"[!] В папке {image_dir} не найдено изображений")

    return filtered_files


def ensure_output_dir(output_dir: str) -> None:
    """Ensure the output directory exists, creating it if necessary.

    Args:
        output_dir: Path to the output directory.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output directory created: {output_dir}")
    elif not os.path.isdir(output_dir):
        raise NotADirectoryError(f"Output path exists but is not a directory: {output_dir}")
