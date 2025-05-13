from pathlib import Path
from PIL import Image, ImageTk

def resize_image(image, size):
    """Resize an image to the specified size."""
    return image.resize(size, Image.Resampling.LANCZOS)