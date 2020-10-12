import numpy as np
import cv2
import time
from PIL import Image
from edgetpu.detection.engine import DetectionEngine
from tflite_runtime.interpreter import Interpreter
from tflite_runtime.interpreter import load_delegate
# from bluetooth import *

"""load labels"""
def load_labels(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        labels = {}
        for line in lines:
            id, name = line.strip().split(maxsplit=1)
            labels[int(id)] = name
    return labels

"""draws the bounding box and label"""
def annotate_objects(frame, coordinate, label_text, accuracy, box_color):
    box_left, box_top, box_right, box_bottom = coordinate

    cv2.rectangle(frame, (box_left, box_top), (box_right, box_bottom), box_color, 2)
    (txt_w, txt_h), base = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_PLAIN, 2, 3)
    cv2.rectangle(frame, (box_left - 1, box_top - txt_h), (box_left + txt_w, box_top + txt_h), box_color, -1)
    cv2.putText(frame, label_text, (box_left, box_top+base), cv2.FONT_HERSHEY_PLAIN, 2, (255,255,255), 2)

"""crop the image to 224*224 and return numpy array"""
def crop_image(image, coordinate):
    y = coordinate[3] - coordinate[1]
    x = coordinate[2] - coordinate[0]
    if x >= y:
        gap = (x - y)/2.0
        coordinate[1] -= gap
        coordinate[3] += gap
    else:
        gap = (y - x)/2.0
        coordinate[0] -= gap
        coordinate[2] += gap

    coordinate = tuple(map(int, coordinate))
    image = image.crop(coordinate).resize((224, 224))
    image = np.expand_dims(np.uint8(image), 0)
    return image

# def set_input_tensor(interpreter, image):
#     """sets the input tensor"""
#     tensor_index = interpreter.get_input_details()[0]['index']
#     input_tensor = interpreter.tensor(tensor_index)()[0]
#     input_tensor[:, :] = image

# def get_output_tensor(interpreter, index):
#     """returns the output tensor at the given index"""
#     output_details = interpreter.get_output_details()[index]
#     tensor = np.squeeze(interpreter.get_tensor(output_details['index']))
#     return tensor

# def predict_poopee(interpreter, img):
#     print('predict poopee')

def main():
    """set variables"""
    video_number = 0
    label_path = 'coco_labels.txt'
    model_path_for_object = 'mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite'
    model_path_for_poopee = 'poopee_edgetpu.tflite'
    threshold = 0.4
    prevTime = 0 # initializing for calculating fps
    box_colors = {} # initializing for setting color
    # setting pad coordinate

    """load labels for detect object"""
    labels = load_labels(label_path)

    """load engine for detect object"""
    engine = DetectionEngine(model_path_for_object)

    """set interpreter for predict poopee"""
    interpreter = Interpreter(model_path_for_poopee, experimental_delegates=[load_delegate('libedgetpu.so.1.0')])
    interpreter.allocate_tensors()

    """load video"""
    cap = cv2.VideoCapture(video_number)
    while True:
        ret, frame = cap.read()
        if not ret:
            print('cannot read frame')
            break
        img = frame[:, :, ::-1].copy() # BGR to RGB
        img = Image.fromarray(img) # NumPy ndarray to PIL.Image

        """detect object"""
        candidates = engine.detect_with_image(img, threshold=threshold, top_k=len(labels), keep_aspect_ratio=True, relative_coord=False, resample=0)
        if candidates:
            for obj in candidates:
                """set color for drawing"""
                if obj.label_id in box_colors:
                    box_color = box_colors[obj.label_id] # the same color for the same object
                else:
                    box_color = [int(j) for j in np.random.randint(0,255, 3)] # random color for new object
                    box_colors[obj.label_id] = box_color

                coordinate = tuple(map(int, obj.bounding_box.ravel()))
                accuracy = int(obj.score * 100) 
                label_text = labels[obj.label_id] + ' (' + str(accuracy) + '%)'
                """draws the bounding box and label"""
                annotate_objects(frame, coordinate, label_text, accuracy, box_color)

                if obj.label_id == 17: # id 17 is dog
                    """crop the image"""
                    input_data = crop_image(img, obj.bounding_box.ravel())

                    """
                    predict poopee
                    0 --> poo
                    1 --> nothing
                    2 --> pee
                    """
                    # Get input and output tensors
                    input_details = interpreter.get_input_details()
                    output_details = interpreter.get_output_details()

                    #input 전달
                    interpreter.set_tensor(input_details[0]['index'], input_data)
                    interpreter.invoke()

                    #Get output
                    output_data = interpreter.get_tensor(output_details[0]['index'])
                    result = np.argmax(output_data)

                    print("dog's coordinate is", coordinate, end=' ')
                    if result == 0:
                        print('and dog poop')
                    elif result == 2:
                        print('and dog pees')
                    else:
                        print('')

                    """send a signal to the snack bar if the dog defecates on the pad"""
                    # compare the dog's coordinates with the set pad's coordinates

        """calculating and drawing fps"""            
        currTime = time.time()
        fps = 1/ (currTime -  prevTime)
        prevTime = currTime
        # print('fps is', fps)
        cv2.putText(frame, "fps:%.1f"%fps, (10,30), cv2.FONT_HERSHEY_PLAIN, 2, (0,255,0), 2)

        """show video"""
        cv2.imshow('goodpp', frame)
        if cv2.waitKey(1)&0xFF == ord('q'):
            break # press q to break
    cap.release()

if __name__ == '__main__':
    main()