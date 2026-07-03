from know_your_specimen.initialization import InitModule
from know_your_specimen.segmentation import process_file


def main():
    # Initialize the image path using the InitModule
    image_path = InitModule.get_image_path()
    output_dir = InitModule.get_output_dir()

    process_file(image_path, output_dir)

    if image_path:
        print(f"Image loaded successfully: {image_path}")
        # Add your main application logic here
    else:
        print("Failed to load image, exiting...")


if __name__ == "__main__":
    main()
