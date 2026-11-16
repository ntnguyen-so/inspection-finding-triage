from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import sys
from pathlib import Path

from . import AzureOpenAIProvider, CopilotProvider, InferenceError, InferenceRequest
from .contracts import strict_json


async def run(args: argparse.Namespace) -> dict:
    if args.provider == "azure":
        if args.models or args.executable:
            raise InferenceError(
                "unsupported_control", "--models and --executable apply only to Copilot"
            )
    elif (
        args.azure_auth is not None or args.azure_native_json
        or args.azure_max_completion_tokens is not None
    ):
        raise InferenceError("unsupported_control", "Azure controls require --provider azure")
    request = None
    if not args.models:
        try:
            if args.request == "-":
                text = sys.stdin.read(256_001)
            else:
                with Path(args.request).open(encoding="utf-8") as source:
                    text = source.read(256_001)
            if len(text.encode("utf-8")) > 256_000:
                raise InferenceError("invalid_request", "Request exceeds 256000 bytes")
            body = strict_json(text)
            if not isinstance(body, dict):
                raise InferenceError("invalid_request", "Request must be a JSON object")
            allowed = {field.name for field in dataclasses.fields(InferenceRequest)}
            if set(body) - allowed:
                raise InferenceError("unsupported_control", "Unsupported request fields")
            request = InferenceRequest(**body)
            request.prepared()
        except (OSError, ValueError, TypeError, RecursionError) as error:
            raise InferenceError("invalid_request", "Could not read inference request") from error
    transport = (
        AzureOpenAIProvider(
            auth=args.azure_auth or "api_key",
            native_json_schema=args.azure_native_json,
            max_completion_tokens=args.azure_max_completion_tokens,
        )
        if args.provider == "azure" else CopilotProvider(args.executable)
    )
    async with transport as provider:
        if args.models:
            return {
                "configuration": provider.configuration(),
                "models": provider.models(),
            }
        response = await provider.generate(request)
        return {
            "status": "succeeded",
            "text": response.text,
            "parsed": response.parsed,
            "receipt": response.receipt,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Azure OpenAI or restricted Copilot inference")
    parser.add_argument("--provider", choices=("copilot", "azure"), default="copilot")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--models", action="store_true", help="List account-visible models")
    group.add_argument("--request", help="JSON request path, or - for stdin")
    parser.add_argument("--executable", help="Explicit native Copilot executable")
    parser.add_argument("--azure-auth", choices=("api_key", "entra"))
    parser.add_argument("--azure-native-json", action="store_true")
    parser.add_argument("--azure-max-completion-tokens", type=int)
    args = parser.parse_args()
    try:
        result = asyncio.run(run(args))
    except InferenceError as error:
        print(json.dumps(error.to_dict(), ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
