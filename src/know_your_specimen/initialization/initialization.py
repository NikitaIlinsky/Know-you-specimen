import os
from typing import Optional


def get_image_path_from_console() -> Optional[str]:
    """
    Prompts the user to enter a path to an image file (JPG or PNG) via console input.

    Returns:
        str: The validated image path, or None if the input is invalid
    """
    image_path = input("Please enter the path to your image file (JPG or PNG): ").strip()

    # Check if the path is empty
    if not image_path:
        print("Error: No path provided.")
        return None

    # Check if the file exists
    if not os.path.exists(image_path):
        print(f"Error: File '{image_path}' does not exist.")
        return None

    # Check if the file extension is valid (JPG or PNG)
    valid_extensions = {".jpg", ".jpeg", ".png"}
    file_extension = os.path.splitext(image_path)[1].lower()

    if file_extension not in valid_extensions:
        print(f"Error: Invalid file format. Expected JPG or PNG, got '{file_extension}'.")
        return None

    print(f"Valid image file selected: {image_path}")
    return image_path


def main():
    """Main function to run the initialization process."""
    image_path = get_image_path_from_console()

    if image_path:
        print(f"Processing image: {image_path}")
        # Here you would typically pass the image path to your processing functions
        return image_path
    else:
        print("Initialization failed due to invalid input.")
        return None


if __name__ == "__main__":
    main()
