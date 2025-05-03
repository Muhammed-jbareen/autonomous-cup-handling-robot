import cv2
from picamera2 import Picamera2, Preview, MappedArray
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO
import tensorflow
from multiprocessing.shared_memory import SharedMemory
import struct
import configparser
from shared_protocol import *

config = configparser.ConfigParser()
config.read('config.ini')

shared_memory_name = str(config.get('General', 'shared_memory_name'))

# Maximum number of reports is 20, since a report size is 11
shared_mem = SharedMemory(create=True, size=243, name=shared_memory_name)  # 243 bytes
requested_report_size = 0
build_report = False

image_size = int(config.get('Camera', 'image_size')) # Height = width

# Max image size is 320
if image_size > 320:
	image_size = 320 

# Initializing the shared memory with 0s 
for i in range(222):
    shared_mem.buf[i] = 0

def check_for_report():
    global requested_report_size
    print(shared_mem.buf[REQUEST_SIGNAL_INDEX])
    if shared_mem.buf[REQUEST_SIGNAL_INDEX] == 1:
        shared_mem.buf[REQUEST_SIGNAL_INDEX] = 0
        requested_report_size = shared_mem.buf[REQUESTED_REPORTS_NUMBER_INDEX]
        return True
    return False
    
def is_white_normalized(r, g, b, tolerance=0.03):
    total = r + g + b
    if total == 0:
        return False
    rn, gn, bn = r / total, g / total, b / total
    # Check if normalized values are close to 1/3
    if abs(rn - 1/3) <= tolerance and abs(gn - 1/3) <= tolerance and abs(bn - 1/3) <= tolerance:
        return True
    return False

def get_color(img, box):
    rgb = [0, 0, 0]
    x1 = box[0]
    y1 = box[1]
    x2 = box[2]
    y2 = box[3]
    
    height = img.shape[0]
    width = img.shape[1]
    
    cup_height = y2 - y1
    cup_width = x2 - x1

    #the bounding box is always bigger than the cup, so we have to cut the edges so we get rid of the noise when calculating the color of the cup.
    width_edge_cut = cup_width // 6
    height_edge_cut = cup_height // 6
    if x1 > 0:
        x1 += width_edge_cut
    if x2 < image_size - 1:
        x2 -= width_edge_cut

    if y1 > 0:
        y1 += height_edge_cut
    y2 -= height_edge_cut
    
    for x in range(x1, x2):
        
        for y in range(y1, y2):
            rgb[0] += img[y][x][0]
            rgb[1] += img[y][x][1]
            rgb[2] += img[y][x][2]
    
    size = cup_height * cup_width
    
    rgb[0] /= size
    rgb[1] /= size
    rgb[2] /= size
    return rgb, size/(height*width) 

def process_result(img, results, threshold = 0.6):
    max_conf = 0
    box = []
    for result in results:
        boxesxyxy = result.boxes.xyxy 
        boxesconf = result.boxes.conf 
        for i in range(result.boxes.xyxy.shape[0]):
            if boxesconf[i] < threshold:
                continue

            x1 = int(boxesxyxy[i][0].item())
            y1 = int(boxesxyxy[i][1].item())
            x2 = int(boxesxyxy[i][2].item())
            y2 = int(boxesxyxy[i][3].item())
            
            if max_conf < boxesconf[i]:
                max_conf = boxesconf[i]
                box = [x1, y1, x2, y2]
            top_left = (x1, y1)
            bottom_right = (x2, y2)
            
            cv2.rectangle(img = img, pt1 = top_left, pt2 = bottom_right, color =  (0, 255, 0))

            cv2.putText(img, f'Cup: {result.boxes.conf[i] * 100:.2f}', (x1 -10, y1 - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0))
    return img, max_conf, box
    
def predict(img, cv2_img, threshold = 0.4):
    global model
    results = model.predict(source=img, stream=True, imgsz=256)
    
    img, conf, box = process_result(cv2_img, results, threshold = threshold)
    rgb = []
    cup_relative_size = 0
    if conf != 0:
        rgb, cup_relative_size = get_color(cv2_img, box)
    
    return img, conf, box, rgb, cup_relative_size


# Initialize the camera
picam2 = Picamera2()
model = YOLO("yolov8_model/final_model.pt")

# Create a preview configuration with specified resolution and frame rate
picam2.configure(picam2.create_preview_configuration(raw={"size":(4608,2592)}, main={"size": (image_size, image_size)}))

picam2.start()

counter = 0
raw_report_data = bytearray()

# Loop to continuously capture and process frames
try:
    while True:
        # Capture frame-by-frame
        frame = picam2.capture_array()
        
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
        
        pil_image = Image.fromarray(frame)
        
        frame, conf, box, rgb, cup_relative_size = predict(pil_image, frame)
        print(rgb)
        if check_for_report():
            build_report = True
            counter = requested_report_size - 1
        if conf != 0:
            x1 = box[0]
            x2 = box[2]
            x_center_of_cup = int((x1 + x2) / 2)
            print(x_center_of_cup, 128)
        if build_report:
                
            if conf != 0:
                # 1 means a cup is detected
                shared_mem.buf[counter * REPORT_SIZE + CUP_DETECTION_FLAG] = 1
                
                x1 = box[0]
                x2 = box[2]
                x_center_of_cup = int((x1 + x2) / 2)
                
                shared_mem.buf[counter * REPORT_SIZE + X_CENTER_INDEX] = x_center_of_cup
                print(x_center_of_cup)
                
                # rgb array is in format of bgr
                b = rgb[0]
                g = rgb[1]
                r = rgb[2]
                
                sum_colors = r + g + b
                
                r_per = r / sum_colors
                g_per = g / sum_colors
                b_per = b / sum_colors
                
                if r_per > 0.5 and g_per < 0.4 and b_per < 0.4:
                    shared_mem.buf[counter * REPORT_SIZE + CUP_COLOR_CLASS_INDEX] = 1 # 1 means the detected cup is likely red
                #elif r > 100 and g > 100 and b > 100:
                elif is_white_normalized(r, g, b):
                    shared_mem.buf[counter * REPORT_SIZE + CUP_COLOR_CLASS_INDEX] = 0 # 0 means the detected cup is likely white
                
                packed_cup_relative_size = struct.pack('d', cup_relative_size)
                
                shared_mem.buf[counter*REPORT_SIZE + RELATIVE_SIZE_INDEX_START: counter * REPORT_SIZE + RELATIVE_SIZE_INDEX_END] = packed_cup_relative_size[0:8]
            else:
                shared_mem.buf[counter * REPORT_SIZE + CUP_DETECTION_FLAG] = 0 # 0 means no cup was detected
            
            counter -= 1
            
            if counter < 0:
                build_report = False
                # Signaling to the reader that the data is ready to read.
                shared_mem.buf[COMPLETION_SIGNAL_INDEX] = 1
                
        cv2.imshow("Video", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
finally:
    # Clean up
    picam2.stop()
    cv2.destroyAllWindows()
    shared_mem.close()
    shared_mem.unlink()

