# MY_AWS_PROJECTS

AWS projects built step by step, documented with real outputs only.
Owner: Haileab T. Bekele — GitHub: Ha113ab, LinkedIn: linkedin.com/in/haileab-bekele

## Projects in this repo

### Project 2 — Image Labels Generator with Amazon Rekognition
Folder: `project-2-rekognition/`

A Python script in AWS CloudShell that calls Amazon Rekognition
DetectLabels on a local image and prints the labels and confidence
scores Rekognition actually returned.

- Script: `project-2-rekognition/detect_labels.py`
- Test image: `project-2-rekognition/test.jpg`
- Test output: `project-2-rekognition/sample-output-test.jpg.txt`
- Full write-up, test results, limits, and 2-minute demo script:
  `project-2-rekognition/README.md`

Example output (test.jpg, us-east-1):
Summer 100.0%, Nature 99.6%, Outdoors 99.6%, Sea 99.6%,
Water 99.6%, Sky 98.8%, Horizon 98.8%, Beach 98.7%,
Scenery 89.0%, Airplane 84.3%

This version is a command-line script, not a website, and it does
not use S3, Lambda, or API Gateway.

## Other projects

Project 1 (PartyRock daily task scheduler) is paused, not cancelled:
the current PartyRock UI has no free-form app builder, only a
challenge library and a Flow builder. Other AWS AI and course
projects will be added here as they are built, documented, and
explainable — nothing is added to a resume until it meets that gate.
