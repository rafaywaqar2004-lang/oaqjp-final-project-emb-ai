"""Flask web application that exposes the emotion detector."""
from flask import Flask, render_template, request

from EmotionDetection.emotion_detection import emotion_detector

app = Flask("Emotion Detector")


@app.route("/emotionDetector")
def emotion_detector_route():
    """Run emotion detection on the textToAnalyze query parameter."""
    text_to_analyze = request.args.get("textToAnalyze", "")

    if not text_to_analyze or not text_to_analyze.strip():
        return "Invalid text! Please try again!", 400

    response = emotion_detector(text_to_analyze)
    dominant_emotion = response["dominant_emotion"]

    if dominant_emotion is None:
        return "Invalid text! Please try again!", 400

    return (
        "For the given statement, the system response is 'anger': "
        f"{response['anger']}, 'disgust': {response['disgust']}, "
        f"'fear': {response['fear']}, 'joy': {response['joy']} and "
        f"'sadness': {response['sadness']}. The dominant emotion is "
        f"{dominant_emotion}."
    )


@app.route("/")
def render_index_page():
    """Serve the application's home page."""
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
