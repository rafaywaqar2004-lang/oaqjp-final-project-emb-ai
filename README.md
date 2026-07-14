# Emotion Detector

An AI-based web application that analyzes customer feedback text and identifies
the dominant emotion expressed (anger, disgust, fear, joy, or sadness), built
with IBM Watson NLP and deployed as a Flask web app.

## Project structure

```
.
├── EmotionDetection/
│   ├── __init__.py
│   └── emotion_detection.py   # emotion_detector() — calls Watson NLP EmotionPredict
├── templates/
│   └── index.html             # web UI
├── static/
│   └── mywebscript.js         # client-side AJAX call to /emotionDetector
├── server.py                  # Flask app (routes: /, /emotionDetector)
├── test_emotion_detection.py  # unittest suite
└── requirements.txt
```

## How it works

1. `EmotionDetection/emotion_detection.py` sends the input text to the Watson
   NLP `EmotionPredict` service and returns a dictionary of scores for anger,
   disgust, fear, joy, and sadness, plus the `dominant_emotion` (the emotion
   with the highest score).
2. `server.py` exposes this function through a Flask web app:
   - `GET /` renders the input form (`templates/index.html`).
   - `GET /emotionDetector?textToAnalyze=<text>` runs emotion detection and
     returns a formatted, human-readable response.
3. Blank or invalid input is rejected with a `400` response and the message
   `Invalid text! Please try again!`, both client-side (`static/mywebscript.js`)
   and server-side (`server.py`, `emotion_detection.py`).

## Running locally

```bash
pip install -r requirements.txt
python server.py
```

Then open `http://localhost:5000` in a browser.

> **Note:** `emotion_detector()` calls the Watson NLP `EmotionPredict` service
> at `sn-watson-emotion.labs.skills.network`, which is only reachable from
> within the IBM Skills Network lab/Cloud IDE environment (or an equivalent
> environment with the Watson NLP container running). Running the app outside
> that environment will return connection errors for any non-blank input.

## Running the unit tests

```bash
python -m unittest test_emotion_detection.py
```

## Static code analysis

```bash
pylint server.py EmotionDetection/emotion_detection.py test_emotion_detection.py
```
