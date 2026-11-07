import threading
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


class OCRService:
    """Extract printed text from uploaded images using EasyOCR."""

    MAX_IMAGE_BYTES = 8 * 1024 * 1024
    MAX_IMAGE_PIXELS = 20_000_000

    def __init__(self, languages=None):
        # English is a compact compatible default; EasyOCR is initialized lazily.
        self.languages = languages or ['en']
        self._reader = None
        self._reader_lock = threading.Lock()

    def _get_reader(self):
        if self._reader is None:
            with self._reader_lock:
                if self._reader is None:
                    import easyocr
                    self._reader = easyocr.Reader(self.languages, gpu=False)
        return self._reader

    def extract_text(self, image_bytes):
        if not image_bytes:
            raise ValueError('Please upload an image.')
        if len(image_bytes) > self.MAX_IMAGE_BYTES:
            raise ValueError('Image exceeds the 8 MB upload limit.')

        try:
            with Image.open(BytesIO(image_bytes)) as image:
                if image.width * image.height > self.MAX_IMAGE_PIXELS:
                    raise ValueError('Image dimensions are too large.')
                image.verify()

            with Image.open(BytesIO(image_bytes)) as image:
                image = ImageOps.exif_transpose(image).convert('RGB')
                if image.width * image.height > self.MAX_IMAGE_PIXELS:
                    raise ValueError('Image dimensions are too large.')
                import numpy as np
                image_array = np.asarray(image)
        except ValueError:
            raise
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError('The uploaded file is not a valid supported image.') from exc

        try:
            text_parts = self._get_reader().readtext(
                image_array,
                detail=0,
                paragraph=True,
            )
        except Exception as exc:
            raise RuntimeError('OCR could not process this image.') from exc

        extracted_text = '\n'.join(
            part.strip() for part in text_parts
            if isinstance(part, str) and part.strip()
        )
        if not extracted_text:
            raise ValueError('No readable text was found in the image.')
        return extracted_text
