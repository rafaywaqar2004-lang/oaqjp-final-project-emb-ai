"""Emotion detection using the Watson NLP EmotionPredict service."""
import json

import requests

WATSON_EMOTION_URL = (
    "https://sn-watson-emotion.labs.skills.network/v1/watson.runtime.nlp.v1/"
    "NlpService/EmotionPredict"
)
MODEL_HEADER = {"grpc-metadata-mm-model-id": "emotion_aggregated-workflow_lang_en_stock"}


def emotion_detector(text_to_analyze):
    """Send text to the Watson NLP EmotionPredict service and return emotion scores.

    Returns a dict with anger, disgust, fear, joy, sadness scores and the
    dominant_emotion. All values are None when the input text is blank or
    otherwise rejected by the service (HTTP 400).
    """
    input_json = {"raw_document": {"text": text_to_analyze}}
    response = requests.post(WATSON_EMOTION_URL, json=input_json, headers=MODEL_HEADER, timeout=10)

    if response.status_code == 400:
        return {
            "anger": None,
            "disgust": None,
            "fear": None,
            "joy": None,
            "sadness": None,
            "dominant_emotion": None,
        }

    formatted_response = json.loads(response.text)
    emotions = formatted_response["emotionPredictions"][0]["emotion"]

    scores = {
        "anger": emotions["anger"],
        "disgust": emotions["disgust"],
        "fear": emotions["fear"],
        "joy": emotions["joy"],
        "sadness": emotions["sadness"],
    }
    scores["dominant_emotion"] = max(scores, key=scores.get)

    return scores
