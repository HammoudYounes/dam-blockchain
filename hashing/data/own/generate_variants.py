import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from pathlib import Path
from random import randint
import shutil


# =========================
# Image Editor Module
# =========================

"""Load an image from a file path or URI, normalised to RGB.

P (palette) and RGBA sources break four of the transforms below: channel_shift rolls
axis 2, which a 2-D palette array does not have; filter_kernel rejects mode P; and
JPEG can encode neither, so encode_quality dies. Every hasher converts to L or RGB
first anyway, so normalising here changes no benchmark result and keeps the variant
set uniform across source formats.

`filename` is restored after convert() — PIL drops it on the new object, and
apply_and_save reads it for the CSV's original_image column. Stored as a POSIX path
so the CSV is identical whichever platform generated it.
"""
def load(image_uri):
    image = Image.open(image_uri)
    source = Path(getattr(image, "filename", None) or str(image_uri)).as_posix()
    if image.mode != "RGB":
        image = image.convert("RGB")
    image.filename = source
    return image


"""Save an image to a file path or URI."""
def save(image, output_uri):
    image.save(output_uri)

"""Resize image to new_size (width, height)."""
def resize(image, new_size):
    return image.resize(new_size)
    
"""Randomly alter a percentage of pixels in the image."""
def alter_pixels(image, pourcentage):
    img_array = np.array(image)
    mask = np.random.rand(*img_array.shape[:2]) < (pourcentage / 100.0)
    random_pixels = np.random.randint(0, 256, img_array.shape, dtype=img_array.dtype)
    img_array[mask] = random_pixels[mask]
    return Image.fromarray(img_array)

 
"""Convert image to grayscale."""
def grayscale(image):
    return image.convert("L")
    
"""Cover a random block of the image with black pixels."""
def cover(image, pourcentage):
    width, height = image.size
    cover_width = int(width * pourcentage / 100)
    cover_height = int(height * pourcentage / 100)
    cover_image = image.copy()
    start_x = randint(0, width - cover_width)
    start_y = randint(0, height - cover_height)
    for i in range(start_x, start_x + cover_width):
        for j in range(start_y, start_y + cover_height):
            cover_image.putpixel((i, j), (0, 0, 0))
    return cover_image

"""Apply grid dropout (random black blocks) to the image."""
def grid_dropout(image, pourcentage):
    dropout_size = 30
    img_array = np.array(image)
    h, w = img_array.shape[:2]
    for i in range(0, h, dropout_size):
        for j in range(0, w, dropout_size):
            if np.random.rand() < (pourcentage / 100.0):
                x_end = min(i + dropout_size, h)
                y_end = min(j + dropout_size, w)
                img_array[i:x_end, j:y_end] = 0
    return Image.fromarray(img_array)
    
"""Apply a Gaussian blur to the image with a given radius."""
def blur(image, radius):
    return image.filter(ImageFilter.GaussianBlur(radius))

"""Adjust brightness by a given factor."""
def brightness(image, factor):
    enhancer = ImageEnhance.Brightness(image)
    return enhancer.enhance(factor)
    
"""Adjust contrast by a given factor."""
def contrast(image, factor):
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(factor)

"""Apply a custom kernel filter to the image."""
def filter_kernel(image, kernel):
    kernel_size = int(np.sqrt(len(kernel)))
    kernel_filter = ImageFilter.Kernel((kernel_size, kernel_size), kernel)
    return image.filter(kernel_filter)

"""Shift image color channels by a given amount."""
def channel_shift(image, shift):
    img_array = np.array(image)
    img_array = np.roll(img_array, shift, axis=2)
    return Image.fromarray(img_array)

"""Apply a transformation to an image and save the result."""
def apply_and_save(image, output_uri, transformation, transformation_name, output_csv_path=None):
    transformed_image = transformation(image)
    if transformed_image is not None:
        save(transformed_image, output_uri)
        if output_csv_path is not None:
            with open(output_csv_path, "a") as f:
                f.write(f"{getattr(image, 'filename', '')},{Path(output_uri).as_posix()},{transformation_name}\n")


"""Crop the image to a specified box (left, upper, right, lower)."""
def crop(image, box):
    return image.crop(box)

"""Encode quality of the image by adjusting its compression level."""
def encode_quality(image, quality, output_uri, output_csv_path, quality_name=None):
    image.save(output_uri, quality=quality)
    if output_csv_path is not None:
        name = quality_name or f"quality_{quality}"
        with open(output_csv_path, "a") as f:
            f.write(f"{getattr(image, 'filename', '')},{Path(output_uri).as_posix()},{name}\n")
"""
Main code
"""

def main():
    src_folder_path = Path("./images")
    output_folder_path = Path("./images_variants")
    output_csv_path = Path("./variants.csv")
    extensions = ".png"


    # Remove all files in the output folder before processing if it exists, otherwise create it
    output_folder_path.mkdir(exist_ok=True)
    for file in output_folder_path.iterdir():
        if file.is_file() or file.is_symlink():
            file.unlink()
        elif file.is_dir():
            shutil.rmtree(file)

    # Create the CSV file and write the header
    if output_csv_path.exists():
        output_csv_path.unlink()
    with output_csv_path.open("w") as csv_file:
        csv_file.write("original_image,variant_image,transformation\n")

    # Process each image in the source folder
    for file in src_folder_path.iterdir():
        print(f"Processing file: {file.name}")
        file_name = file.stem
        file_output_dir = output_folder_path / file_name
        file_output_dir.mkdir(exist_ok=True)
        image = load(file)
        if image:
            # random pixel 
            apply_and_save(image, f"{file_output_dir}/altered{extensions}", lambda img: alter_pixels(img, 20), "altered_20%", output_csv_path)

            # grayscale
            apply_and_save(image, f"{file_output_dir}/grayscale{extensions}", grayscale, "grayscale", output_csv_path)

            # image covered with black block
            apply_and_save(image, f"{file_output_dir}/covered{extensions}", lambda img: cover(img, 30), "covered_30%", output_csv_path)

            # image covered with black blocks in a grid pattern
            apply_and_save(image, f"{file_output_dir}/dropout{extensions}", lambda img: grid_dropout(img, 20), "grid_dropout_20%", output_csv_path)

            # blurred image
            apply_and_save(image, f"{file_output_dir}/blurred{extensions}", lambda img: blur(img, 2), "blur_radius_2", output_csv_path)

            # brightness adjusted image
            apply_and_save(image, f"{file_output_dir}/brightened{extensions}", lambda img: brightness(img, 1.5), "brightened_1.5x", output_csv_path)

            # brightness reduced image
            apply_and_save(image, f"{file_output_dir}/darkened{extensions}", lambda img: brightness(img, 0.5), "darkened_0.5x", output_csv_path)

            # resized image 
            apply_and_save(image, f"{file_output_dir}/resized{extensions}", lambda img: resize(img, (img.width // 2, img.height // 2)), "resized_50%", output_csv_path)

            # resized image up 
            apply_and_save(image, f"{file_output_dir}/resized_up{extensions}", lambda img: resize(img, (img.width * 2, img.height * 2)), "resized_up_200%", output_csv_path)

            # contrast adjusted image
            apply_and_save(image, f"{file_output_dir}/contrasted{extensions}", lambda img: contrast(img, 1.5), "contrast_1.5x", output_csv_path)

            # filtered image
            apply_and_save(image, f"{file_output_dir}/filtered{extensions}", lambda img: filter_kernel(img, [0, -1, 0, -1, 5, -1, 0, -1, 0]), "edge_filter", output_csv_path)

            # channel shifted image
            apply_and_save(image, f"{file_output_dir}/channel_shifted{extensions}", lambda img: channel_shift(img, 1), "channel_shift_1", output_csv_path)

            # crop image with 10%, 20%, 30% border removal
            percents = [10, 20, 30]
            for percent in percents:
                left = int(image.width * percent / 100)
                upper = int(image.height * percent / 100)
                right = int(image.width * (1 - percent / 100))
                lower = int(image.height * (1 - percent / 100))
                apply_and_save(image, f"{file_output_dir}/cropped{percent}{extensions}", lambda img, l=left, u=upper, r=right, lo=lower: crop(img, (l, u, r, lo)), f"cropped_{percent}%", output_csv_path)

            # quality adjusted image    
            encode_quality(image, 20, f"{file_output_dir}/quality_adjusted_20.jpg", output_csv_path, "quality_20%")
            encode_quality(image, 50, f"{file_output_dir}/quality_adjusted_50.jpg", output_csv_path, "quality_50%")
            encode_quality(image, 80, f"{file_output_dir}/quality_adjusted_80.jpg", output_csv_path, "quality_80%")

if __name__ == "__main__":
    main()