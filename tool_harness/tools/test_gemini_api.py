#!/usr/bin/env python3
"""
Lightweight Gemini API Connection Verification Tool.
Tests API key authentication, model generation, latency, and token usage using the official google-genai SDK.
"""

import os
import sys
import time
import argparse
import warnings

# Suppress SDK warnings
warnings.filterwarnings("ignore", category=UserWarning)

try:
    from google import genai
    from google.genai import types
except ImportError:
    sys.exit("Error: 'google-genai' SDK is not installed. Install via: pip install google-genai")


def test_api_connection(api_key: str = "", model: str = "gemini-3.8-flash"):
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("[ERROR] GEMINI_API_KEY environment variable is not set.")
        print(" -> Set it via PowerShell: $env:GEMINI_API_KEY='your_api_key'")
        print(" -> Set it via CMD: set GEMINI_API_KEY=your_api_key")
        print(" -> Or pass directly: python tools/test_gemini_api.py --api-key YOUR_KEY\n")
        return False

    print("==================================================")
    print("  GEMINI API CONNECTION TESTER")
    print("==================================================")
    print(f" Target Model : {model}")
    print(f" API Key      : {key[:6]}...{key[-4:] if len(key) > 10 else ''}")
    print("--------------------------------------------------")
    print("[1/2] Initializing Google GenAI Client...")

    try:
        client = genai.Client(api_key=key)
        print(" [OK] Client initialized successfully.")
    except Exception as exc:
        print(f" [FAIL] Client initialization failed: {exc}")
        return False

    print(f"[2/2] Sending test prompt to model '{model}'...")
    start_time = time.time()

    prompt = "Hello! Please respond with 'Gemini API connection successful!' and a brief one-line greeting."
    
    fallback_models = [model, "gemini-3.7-flash", "gemini-3.6-flash", "gemini-2.5-flash", "gemini-flash-latest"]
    # De-duplicate while preserving order
    seen = set()
    dedup_models = [m for m in fallback_models if not (m in seen or seen.add(m))]

    success = False
    for target_model in dedup_models:
        try:
            print(f" -> Attempting call to model: '{target_model}'...")
            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                ),
            )
            elapsed = time.time() - start_time
            print("\n==================================================")
            print("  CONNECTION TEST PASSED!")
            print("==================================================")
            print(f" Active Model   : {target_model}")
            print(f" Latency        : {elapsed:.2f} seconds")
            
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                meta = response.usage_metadata
                prompt_tokens = getattr(meta, "prompt_token_count", 0) or 0
                cand_tokens = getattr(meta, "candidates_token_count", 0) or 0
                total_tokens = getattr(meta, "total_token_count", 0) or (prompt_tokens + cand_tokens)
                print(f" Token Usage    : Prompt={prompt_tokens}, Output={cand_tokens}, Total={total_tokens}")

            print("\n Model Response:")
            print(f" \"{response.text.strip()}\"")
            print("==================================================\n")
            success = True
            break
        except Exception as exc:
            err_msg = str(exc)
            if "404" in err_msg or "not_found" in err_msg.lower() or "not available" in err_msg.lower():
                print(f" [WARN] Model '{target_model}' returned 404 Not Found. Trying fallback...")
            elif "503" in err_msg or "unavailable" in err_msg.lower() or "busy" in err_msg.lower():
                print(f" [WARN] Model '{target_model}' returned 503 Busy. Trying fallback...")
            else:
                print(f" [FAIL] API call error on '{target_model}': {exc}")

    if not success:
        print("\n==================================================")
        print("  CONNECTION TEST FAILED")
        print("==================================================")
        print(" All attempted models failed. Please check your API key and network connection.")
        print(" You can list available models with: python tools/generate_bsp_examples.py --list-models")
        print("==================================================\n")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Test Gemini API connection and model availability.")
    parser.add_argument("--api-key", type=str, default="", help="Gemini API Key (or set GEMINI_API_KEY env var)")
    parser.add_argument("--model", type=str, default="gemini-3.6-flash", help="Gemini Model ID to test (default: gemini-3.6-flash)")
    args = parser.parse_args()

    success = test_api_connection(api_key=args.api_key, model=args.model)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
