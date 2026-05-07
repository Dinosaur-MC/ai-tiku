import base64

import pytest

from utils.vision_inputs import OllamaPreparedImage, prepare_ollama_image_inputs


def test_prepare_ollama_inputs_keeps_remote_urls_by_default():
    prepared = prepare_ollama_image_inputs(
        ["https://img.test/a.png", "https://img.test/b.png"],
        allow_remote_urls=True,
    )

    assert prepared == [
        OllamaPreparedImage(kind="url", value="https://img.test/a.png"),
        OllamaPreparedImage(kind="url", value="https://img.test/b.png"),
    ]


def test_prepare_ollama_inputs_downloads_and_base64_encodes_when_urls_disallowed(
    monkeypatch,
):
    monkeypatch.setattr(
        "utils.vision_inputs._download_image_bytes",
        lambda url: b"png-bytes-" + url.encode(),
    )

    prepared = prepare_ollama_image_inputs(
        ["https://img.test/a.png"],
        allow_remote_urls=False,
    )

    expected_b64 = base64.b64encode(b"png-bytes-https://img.test/a.png").decode()
    assert prepared == [OllamaPreparedImage(kind="base64", value=expected_b64)]


def test_prepare_ollama_inputs_keeps_explicit_bytes_without_download():
    prepared = prepare_ollama_image_inputs([], raw_images=[b"abc"], allow_remote_urls=False)

    expected_b64 = base64.b64encode(b"abc").decode()
    assert prepared == [OllamaPreparedImage(kind="base64", value=expected_b64)]


def test_prepare_ollama_inputs_raises_when_download_fails(monkeypatch):
    monkeypatch.setattr(
        "utils.vision_inputs._download_image_bytes",
        lambda url: (_ for _ in ()).throw(RuntimeError("download failed")),
    )

    with pytest.raises(RuntimeError, match="download failed"):
        prepare_ollama_image_inputs(["https://img.test/a.png"], allow_remote_urls=False)
