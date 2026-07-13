import unittest
from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image
from starlette.datastructures import Headers

from routes.uploads import read_validated_image


def one_pixel_png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (1, 1), color="white").save(output, format="PNG")
    return output.getvalue()


def make_upload(content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        filename="document.png",
        file=BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


class UploadValidationTests(unittest.TestCase):
    def test_accepts_a_valid_png(self):
        image_bytes = one_pixel_png()
        upload = make_upload(image_bytes, "image/png")

        self.assertEqual(read_validated_image(upload), image_bytes)

    def test_rejects_an_unsupported_content_type(self):
        upload = make_upload(b"not an image", "application/pdf")

        with self.assertRaises(HTTPException) as context:
            read_validated_image(upload)

        self.assertEqual(context.exception.status_code, 415)

    def test_rejects_a_corrupt_image_payload(self):
        upload = make_upload(b"\x89PNG\r\n\x1a\nnot-a-real-png", "image/png")

        with self.assertRaises(HTTPException) as context:
            read_validated_image(upload)

        self.assertEqual(context.exception.status_code, 400)
