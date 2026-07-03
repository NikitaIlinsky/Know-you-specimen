import os

from dotenv import load_dotenv


class Config:
    """Configuration class to manage application settings from environment variables."""

    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        # Default values for configuration
        self.image_input_dir = self.get_env_var("IMAGE_INPUT_DIR", "./input_images")
        self.output_dir = self.get_env_var("OUTPUT_DIR", "./output")
        self.debug_mode = self.get_env_var("DEBUG_MODE", "False").lower() == "true"
        self.model_path = self.get_env_var("MODEL_PATH", "./models/default_model.pth")
        self.segmentation_threshold = float(self.get_env_var("SEGMENTATION_THRESHOLD", "0.5"))
        self.allowed_extensions = self.get_allowed_extensions()

    def get_env_var(self, key: str, default_value: str) -> str:
        """Get environment variable with a fallback default value."""
        return os.getenv(key, default_value)

    def get_allowed_extensions(self) -> set:
        """Get allowed file extensions from environment or use default."""
        extensions_str = self.get_env_var("ALLOWED_EXTENSIONS", ".jpg,.jpeg,.png")
        return {ext.strip().lower() for ext in extensions_str.split(",")}


# Global configuration instance
config = Config()
