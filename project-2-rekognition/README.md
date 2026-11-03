# Project 2 — Image Labels Generator with Amazon Rekognition

Owner: Haileab T. Bekele (GitHub: Ha113ab)
Built: 2026-11-02, AWS CloudShell, region us-east-1
Status: Built and tested. README and demo script are in this file.
Not yet done: GitHub push, cleanup check, and any resume line.
Nothing in this project is claimed as a web app, a production deployment,
or an S3 / Lambda / API Gateway build, because none of those were built
in this version.

## What it does

A small Python script takes a local image file, calls Amazon Rekognition
DetectLabels, and prints the labels Rekognition actually returned, with
their confidence scores, highest first.

Input: a local .jpg or .png image, under 5 MB.
Output: label names and confidence percentages, for example
`Summer: 100.0%`.

## Services and architecture

- Amazon Rekognition — DetectLabels, the only AI service used.
- AWS CloudShell — where the script was run. CloudShell uses the
  console sign-in, so no access keys were created for this step.
- AWS Budgets — a $5 monthly budget with an 80% Forecasted email
  alert, set before any Rekognition use. A budget alert only emails;
  it does not stop spending by itself.

Flow:
Local image file -> CloudShell Python script (boto3) ->
Amazon Rekognition DetectLabels -> printed labels and confidence.

No S3 bucket, no Lambda function, and no API Gateway were created
in this version.

## How to run it

1. In the AWS Console, open CloudShell.
2. Upload a clear .jpg or .png image (under 5 MB) to CloudShell.
   Use a non-private image.
3. Create `detect_labels.py` with the code in this folder.
4. Run, replacing `test.jpg` with your image filename:

```bash
python3 detect_labels.py test.jpg
```

The script uses `MaxLabels=10` and `MinConfidence=70`, so it prints
at most 10 labels, all at 70% confidence or higher.

## Test results — real outputs only, nothing invented

### Test A — Rekognition console demo, sample image
Console: Demos > Label detection, sample city-street skateboarder
image, with bounding boxes on the person, cars, and buildings.
Screenshot: `console-label-detection-demo.png`

- Road: 99.9%
- Street: 99.9%
- Urban: 99.9%
- Person: 98.7%

Note: the "City" box in that screenshot is the "Check whether we
support your label" search, not a detected label. City is not listed
above as a detection result.

### Test B — Script test, CloudShell, us-east-1
Command: `python3 detect_labels.py test.jpg`
Screenshot: `cloudshell-script-output.png`
Full output: `sample-output-test.jpg.txt`

- Summer: 100.0%
- Nature: 99.6%
- Outdoors: 99.6%
- Sea: 99.6%
- Water: 99.6%
- Sky: 98.8%
- Horizon: 98.8%
- Beach: 98.7%
- Scenery: 89.0%
- Airplane: 84.3%

## Limits — say these honestly in an interview

- This version is a command-line script, not a website. There is no
  upload page, no hosted link, and no saved gallery.
- Labels are Rekognition's model output. A confidence score is the
  model's confidence, not a guarantee that the label is correct.
- Images are sent to Rekognition as bytes for that one call. The
  script does not store the image in S3.
- The $5 budget alert is an email warning only. It does not cap or
  stop Rekognition calls.
- Region used for the script test was us-east-1, as shown in the
  CloudShell tabs. Earlier steps assumed us-east-2; that assumption
  was corrected by the screenshot.

## Cleanup

- No S3 bucket, Lambda function, or API Gateway to delete for this
  version.
- To clean up after the demo, delete the test image and the script
  from CloudShell if you do not want them kept there.
- Do NOT delete the $5 budget alert. It is the guardrail for the
  later projects in this track.
- After the demo, check Billing to confirm what the Rekognition
  calls actually cost before moving on.

## 2-minute demo script

"I built an image labels generator with Amazon Rekognition.
First I set a $5 monthly budget with a forecasted alert, so I would
get an email before going over. Then I tested Rekognition in the
console with a sample street image, and it returned Road, Street,
Urban, and Person, all above 98 percent.
Then I built my own version: a short Python script in CloudShell
using boto3. It reads a local image, calls DetectLabels with a
maximum of 10 labels and a 70 percent minimum confidence, and
prints the labels. On my test image it returned Summer at 100
percent, Nature, Outdoors, Sea, and Water at 99.6 percent, and
down to Airplane at 84.3 percent.
This version is a command-line tool, not a website, and it does
not use S3 or Lambda yet. A next step would be adding an upload
page with S3, Lambda, and API Gateway, so someone else could
upload an image and see the labels in a browser."

## Files in this folder

- `detect_labels.py` — the generator script.
- `sample-output-test.jpg.txt` — the verified script output.
- `console-label-detection-demo.png` — console demo screenshot.
- `cloudshell-script-output.png` — CloudShell script screenshot.
- `README.md` — this file.
