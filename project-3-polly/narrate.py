#!/usr/bin/env python3
"""Text narrator using Amazon Polly.

Usage:
    python3 narrate.py "Hello, this is a test." output.mp3
    python3 narrate.py input.txt output.mp3

If the first argument is an existing file, its contents are read as the
text to narrate. Otherwise the first argument itself is the text.
No S3 bucket, Lambda, or API Gateway is created. The MP3 is written
locally. Runs in AWS CloudShell using the console session, so no
access keys are needed.

Default voice: Joanna, English (US), neural engine, MP3 output.
Region: us-east-1, matching the CloudShell region used for Project 2.
"""

import sys

import boto3


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python3 narrate.py "<text or input.txt>" [output.mp3]')
        sys.exit(1)

    first = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "narrated.mp3"

    try:
        with open(first, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except (OSError, UnicodeDecodeError):
        text = first

    if not text:
        print("No text to narrate.")
        sys.exit(1)

    polly = boto3.client("polly", region_name="us-east-1")

    response = polly.synthesize_speech(
        Text=text,
        VoiceId="Joanna",
        Engine="neural",
        LanguageCode="en-US",
        OutputFormat="mp3",
    )

    with open(output_file, "wb") as out:
        out.write(response["AudioStream"].read())

    print(f"Voice: Joanna (en-US, neural)")
    print(f"Characters: {len(text)}")
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()
