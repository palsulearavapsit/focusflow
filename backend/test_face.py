import os, logging
logging.disable(logging.CRITICAL)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from services.face_detector import face_detector

test_img = 'debug_face_fail.jpg'
if os.path.exists(test_img):
    with open(test_img, 'rb') as f:
        data = f.read()
    r = face_detector.detect_faces(data)
    print('RESULT:', 'FACE DETECTED' if r['face_detected'] else 'NO FACE')
    print('Count:', r['face_count'])
    print('Boxes:', r['bounding_boxes'])
    print('Scores:', r['confidence_scores'])
else:
    print('No debug frame available — run a study session first to generate one')
