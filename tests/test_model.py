# ###################################################################
# Ruben Cardenes -- Mar 2020
#
# File:        test_model.py
# Description: This script tests a trained keras model with some image
#
# ###################################################################

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from keras_pilot import KerasLinear, KerasCategorical
import glob
import cv2
import os
import json

###
IMAGE_W = 160
IMAGE_H = 120
input_shape = (IMAGE_H, IMAGE_W, 3)
roi_crop = (0, 0)
kl = None
model_path = ""

# type = 'linear'
type = 'categorical'
if type == 'linear':
    model_path = '../models/pilot_home_day_linear_aug.h5'
    kl = KerasLinear(input_shape=input_shape, roi_crop=roi_crop)
if type == 'categorical':
    model_path = '../models/pilot_home_day_cat_aug2.h5'
    kl = KerasCategorical(input_shape=input_shape, roi_crop=roi_crop)

kl.load(model_path)

# Input Data Test
data_dir = '../images'
image_paths = ["../images/42_test_image_car.jpg"]
#####

# Input Data
# Use this if you want to process a full directory
# data_dir = '/home/ruben/mycar/data/day/tub_5_20-03-08'
# image_paths = [x for x in glob.glob(f"{data_dir}/*.jpg")]
# image_paths.sort(key=lambda x: int(os.path.basename(x)[:os.path.basename(x).find("_")]))
#####

cv2.namedWindow("", cv2.WINDOW_KEEPRATIO)
pause = True
set_break = False
next = False
for image_path in image_paths:
    print(f" processing {image_path}")
    im = cv2.imread(image_path)
    # print(f" im  type {im.dtype} {im.shape}")
    st, th = kl.run(im)
    file_basename = os.path.basename(image_path)
    num = int(file_basename.split("_")[0])
    json_file = os.path.join(data_dir, f"record_{num}.json")
    print('json file ', json_file)
    with open(json_file, 'r') as f:
        data = json.load(f)
    text1 = f"{file_basename} steering {st} throtle {th}"
    text2 = f"AI: steer {st:0.3f} throttle {th:0.3f}"
    text3 = f"GT: steer {data['user/angle']:0.3f} throttle {data['user/throttle']:0.3f}"
    print(text2)
    print(text3)
    cv2.putText(im, text2, (10, 10), cv2.FONT_HERSHEY_SIMPLEX,
                0.25, (255, 255, 255), 1, lineType=cv2.LINE_AA)
    cv2.putText(im, text3, (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                0.25, (255, 255, 255), 1, lineType=cv2.LINE_AA)
    cv2.imshow("", im)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    if key == ord('p'):
        pause = True

    while pause:
        key = cv2.waitKey(1) & 0xFF
        if key == ord('p'):
            pause = False
            next = False
        if key == ord('n'):
            next = True
            break
        if key == ord('q'):
            pause = False
            set_break = True

    if set_break:
        break


