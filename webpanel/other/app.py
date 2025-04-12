import cv2
from flask import Flask, Response

app = Flask(__name__)

def list_available_cameras(max_test=10):
    available_cameras = []
    for index in range(max_test):
        cap = cv2.VideoCapture(index)
        if cap.read()[0]:
            available_cameras.append(index)
        cap.release()
    return available_cameras

def generate_frames():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    while True:
        success, frame = cap.read()
        if not success:
            print("Error: Failed to capture frame.")
            break

        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return '''
    <html>
    <head><title>USB</title></head>
    <body>
    <h1>USB</h1>
    <img src="/video_feed" width="1280" height="720">
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    

