from src.know_your_specimen.config import config
from src.know_your_specimen.initialization.initialization import get_image_paths
from src.know_your_specimen.segmentation.talk_percentage import process_file


def main():
    image_dir = config.image_input_dir
    output_dir = config.output_dir

    images = get_image_paths(image_dir, config.allowed_extensions)
    for image_path in images:
        process_file(image_path, output_dir)


if __name__ == "__main__":
    main()
