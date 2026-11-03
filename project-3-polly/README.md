# Project 3 — Text Narrator with Amazon Polly

## What it does

A command-line text narrator. You give it text, or a text file, and it
uses Amazon Polly to turn that text into spoken audio, saved as an MP3
file you can play back.

It is not a website, and it does not have an upload page or a hosted
player. It is a working Python script with real Polly output, verified
in the AWS console and in CloudShell.

## Architecture / services used

- Amazon Polly — `synthesize_speech`, text-to-speech
- AWS CloudShell — runs the script using the console session
- AWS Budgets — the $5 monthly budget alert from Project 2, reused
  here; no new budget was created for Project 3

No S3 bucket, Lambda function, or API Gateway was created in this
version. No access keys were needed, because CloudShell uses the
console session.

## How to run it

From CloudShell, in the folder containing `narrate.py`:

```bash
python3 narrate.py "Hello, this is a test of Amazon Polly. I built a text narrator that turns written words into spoken audio." narrated.mp3
```

Or, with a text file as input:

```bash
python3 narrate.py input.txt output.mp3
```

Default settings in `narrate.py`:

- Voice: Joanna
- Language: English (US), `en-US`
- Engine: neural
- Output format: MP3
- Region: `us-east-1`, matching the CloudShell region used for Project 2

The script prints the voice, the character count, and the output file
name, then saves the MP3 locally.

## Real test results

### Test 1 — Polly console test, 2026-11-02

Polly console Text-to-Speech test, with the short test text above.
The console MP3 download is saved here as `console-test-output.mp3`
(40 KB, MPEG Layer III, 48 kbps, 24 kHz, mono).

The console voice used for this first test was not recorded, so no
specific console voice is claimed here. The script test below is the
voice-specific result.

### Test 2 — CloudShell script test, 2026-11-02, verified from screenshot

Command run in CloudShell, region `us-east-1`:

```bash
python3 narrate.py "Hello, this is a test of Amazon Polly. I built a text narrator that turns written words into spoken audio." narrated.mp3
```

Output, with no error:

```
Voice: Joanna (en-US, neural)
Characters: 106
Saved: narrated.mp3
```

Screenshot of this run is saved here as `cloudshell-script-output.png`.

The script output `narrated.mp3` is saved in this folder, downloaded
from CloudShell after the run above. It is a different file from the
console test MP3 (same size and format, different file hash), as
expected for two separate Polly syntheses of the same short text.

## Limits — what this is not

- Not a website or web app; there is no hosted link to play audio in
  a browser.
- Not a long-form audiobook tool; tests were kept to one short
  sentence on purpose, because the $5 budget forecast was already
  close to the limit ($4.95 forecasted, $0.00 actual, at the Project 3
  budget check).
- The budget alert only emails; it does not cap or stop spending.
- Polly output quality and voice are Polly model output; this project
  does not claim human-recorded audio.

## Cleanup

- No S3 bucket, Lambda, or API Gateway exists to delete for this
  version.
- Delete `narrate.py` and any test MP3s from CloudShell only if you
  want to; keeping them does not by itself keep charging.
- Do NOT delete the $5 `AI-projects-monthly-5` budget alert. It is
  the guardrail for later projects in this track.
- Check Billing for actual Polly cost after the tests.

## 2-minute demo script

1. "This is Project 3, a text narrator with Amazon Polly."
2. "First I tested it in the Polly console, and downloaded the MP3."
3. "Then I built a Python script in CloudShell that calls Polly's
   synthesize_speech, with voice Joanna, English US, neural engine."
4. "I ran it on one short sentence, 106 characters, and it saved
   narrated.mp3 with no error."
5. "It is a command-line tool, not a website, and it creates no S3
   bucket or Lambda. The code, the console MP3, and the CloudShell
   screenshot are in the project folder."

## Files in this folder

- `narrate.py` — the narrator script
- `console-test-output.mp3` — Polly console test MP3, 40 KB
- `cloudshell-script-output.png` — screenshot of the script run
- `README.md` — this file
- `narrated.mp3` — CloudShell script output, Joanna neural, 40 KB
