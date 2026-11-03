"""Image Labels Generator - Amazon Rekognition (Project 2, Step 3).

Usage (in AWS CloudShell, in the same region as the console session):
    python3 detect_labels.py test.jpg

Reads a local image file (.jpg or .png, under 5 MB), calls
Rekognition DetectLabels, and prints each label with its confidence
score, highest first. No image is stored by this script; Rekognition
is called with the image bytes only. No S3 bucket, Lambda function,
or API Gateway is created by this step.
"""

import sys

import boto3


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 detect_labels.py <image-file>")
        raise SystemExit(1)

    image_path = sys.argv[1]
    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    client = boto3.client("rekognition")
    response = client.detect_labels(
        Image={"Bytes": image_bytes},
        MaxLabels=10,
        MinConfidence=70,
    )

    print(f"Image: {image_path}")
    for label in response["Labels"]:
        print(f"{label['Name']}: {label['Confidence']:.1f}%")


if __name__ == "__main__":
    main()
