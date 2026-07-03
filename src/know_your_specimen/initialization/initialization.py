import os
from typing import Optional


class InitModule:
    @staticmethod
    def _get_image_path_from_console() -> Optional[str]:
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

    @staticmethod
    def get_output_dir() -> Optional[str]:
        """
        Prompts the user to enter a path for output directory via console input.
        Ensures the directory exists or creates it.

        Returns:
            str: The validated output directory path, or None if the input is invalid
        """
        output_path = input("Please enter the path for output directory: ").strip()

        # Check if the path is empty
        if not output_path:
            print("Error: No output directory provided.")
            return None

        # Expand user path if needed (e.g., ~/Documents)
        output_path = os.path.expanduser(output_path)

        # If the path doesn't end with a separator, append one to ensure it's treated as a directory
        if not output_path.endswith((os.sep, "/")):
            output_path += os.sep

        # Create directory if it doesn't exist
        if not os.path.exists(output_path):
            try:
                os.makedirs(output_path, exist_ok=True)
                print(f"Created output directory: {output_path}")
            except OSError as e:
                print(f"Error: Could not create directory '{output_path}'. {str(e)}")
                return None

        print(f"Output directory set to: {output_path}")
        return output_path

    @staticmethod
    def get_image_path():
        """Main function to run the initialization process."""
        image_path = InitModule._get_image_path_from_console()

        if image_path:
            print(f"Processing image: {image_path}")
            # Here you would typically pass the image path to your processing functions
            return image_path
        else:
            print("Initialization failed due to invalid input.")
            return None
