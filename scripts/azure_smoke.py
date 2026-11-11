"""Run one explicitly authorized synthetic Azure probe, or use offline fixtures."""

import argparse
import json
from typing import cast

from pydantic import ValidationError

from apps.api.multimodal import AzureProvider, AzureSettings, Capability, FixtureProvider
from packages.domain.design import DomainError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capability", choices=["chat", "vision", "image", "embedding"])
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--allow-charges", action="store_true")
    parser.add_argument("--allow-image-generation", action="store_true")
    options = parser.parse_args()
    capability = cast(Capability, options.capability)
    if options.live and (
        not options.allow_charges or (capability == "image" and not options.allow_image_generation)
    ):
        parser.error(
            "Live calls require --allow-charges; image also needs --allow-image-generation"
        )
    fixture = FixtureProvider()
    jpeg = (
        fixture.run("image", "Synthetic reference").thumbnail_jpeg
        if capability == "vision"
        else None
    )
    try:
        provider = AzureProvider(AzureSettings()) if options.live else fixture
        result = provider.run(
            capability, "Describe a synthetic garment sketch. No geometry edits.", jpeg
        )
    except DomainError as exc:
        print(
            json.dumps(
                {
                    "status": "skipped" if exc.code == "azure_capability_disabled" else "failed",
                    "code": exc.code,
                }
            )
        )
        return 2 if exc.code == "azure_capability_disabled" else 1
    except ValidationError:
        print('{"status":"failed","code":"invalid_azure_configuration"}')
        return 1
    print(
        result.model_dump_json(exclude={"thumbnail_jpeg", "analysis", "vector"}, exclude_none=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
