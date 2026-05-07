from __future__ import annotations

import base64
from dataclasses import dataclass
from urllib.request import urlopen


@dataclass(eq=True)
class OllamaPreparedImage:
    kind: str
    value: str


def _download_image_bytes(url: str) -> bytes:
    with urlopen(url) as response:
        return response.read()


def _encode_image_bytes(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode()


def prepare_ollama_image_inputs(
    image_urls: list[str],
    raw_images: list[bytes] | None = None,
    allow_remote_urls: bool = True,
) -> list[OllamaPreparedImage]:
    prepared: list[OllamaPreparedImage] = []

    for image_url in image_urls:
        if allow_remote_urls:
            prepared.append(OllamaPreparedImage(kind="url", value=image_url))
        else:
            prepared.append(
                OllamaPreparedImage(
                    kind="base64",
                    value=_encode_image_bytes(_download_image_bytes(image_url)),
                )
            )

    for raw_image in raw_images or []:
        prepared.append(
            OllamaPreparedImage(kind="base64", value=_encode_image_bytes(raw_image))
        )

    return prepared
