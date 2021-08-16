#!/usr/bin/env python3

# Send a full path of an mp4 file to the port and this code
# will scan all of the event images. If it detects an object
# from the COCO dataset, it will move the movie file to a
# target folder. The movie file must start with an %v, and
# so must its component images, that is how the program
# determines which images are associated with the movie.

import os
import pathlib
import socket
import time
import re
import glob

from threading import Thread
from collections import deque

from pycoral.utils import edgetpu
from pycoral.utils import dataset
from pycoral.adapters import common
from pycoral.adapters import classify
from pycoral.adapters import detect
from PIL import Image

SAVE_DIR="/media/usbdisk/motion/saves/"
PORT=19011

class QueueThread(Thread):
    def __init__(self, serversocket, q):
        Thread.__init__(self)
        self.serversocket = serversocket
        self.q = q

    def run(self):
        while True:
            time.sleep(0.001)
            try:
                clientsocket, address = self.serversocket.accept()
                data = clientsocket.recv(1024)
                if data:
                    print("Queue:", data)
                    self.q.append(data.decode('utf-8'))
                clientsocket.close()
            except:
                print('Exiting QueueThread on exception')
                break

class DetectThread(Thread):
    def __init__(self, q):
        Thread.__init__(self)
        
        self.q = q
        
        script_dir = pathlib.Path(__file__).parent.absolute()
        model_file = os.path.join(
                script_dir,
                'ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite')
        label_file = os.path.join(script_dir, 'coco_labels.txt')
        self.labels = dataset.read_label_file(label_file)
        self.interpreter = edgetpu.make_interpreter(model_file)
        self.interpreter.allocate_tensors()
        print("Model loaded")
        
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.bind((socket.gethostname(), PORT))
        self.serversocket.listen(5)
        print("Listening on port", PORT)

    def check_image_file(self, fn):
        image = Image.open(fn)
        _, scale = common.set_resized_input(
                self.interpreter,
                image.size,
                lambda size: image.resize(size, Image.ANTIALIAS))
        self.interpreter.invoke()
        objs = detect.get_objects(self.interpreter, 0.50, scale)
        count = 0
        if not objs:
            print("...no objects")
            pass
        else:
            print("...found:")
            for obj in objs:
                print(self.labels.get(obj.id, obj.id), obj.id, obj.score, obj.bbox)
                count = count + 1
        return count

    def process_file(self, fn):
        try:
            if self.check_image_file(fn) > 0:
                response = 'yes'
                return 1
            else:
                response = 'no'
        except:
            response = 'fail'
        return 0

    def run(self):
        while True:
            time.sleep(0.001)
            if len(self.q) > 0:
                fn = self.q.popleft()
                if fn == 'exit':
                    break
                if os.path.exists(fn) and re.match(r'.*\.mp4$', fn):
                    index = fn.split('-')[0]
                    images = glob.glob(index + '-*.jpg')
                    save = False
                    print("Checking %d images in %s" % (len(images), fn))
                    x = 0
                    first_image = None
                    for image in images:
                        x = x + 1
                        print("check_image_file(%s) [%d/%d]" % (image, x, len(images)), end='')
                        if self.process_file(image):
                            save = True
                            first_image = image
                            break
                    if save:
                        print("...saving this movie (and the first detected image)")
                        os.rename(fn, SAVE_DIR + os.path.basename(fn))
                        os.rename(first_image, SAVE_DIR + os.path.basename(first_image))
                    else:
                        print("...nothing to save")
                elif os.path.exists(fn) and re.match(r'.*\.jpg$', fn):
                    print("Checking a single image (not moving it)")
                    self.process_file(fn)
                else:
                    print("not movie")
        self.serversocket.close()

def main():
    masterQueue = deque()
    detectThread = DetectThread(masterQueue)
    queueThread = QueueThread(detectThread.serversocket, masterQueue)
    queueThread.start()
    detectThread.start()
    detectThread.join()

if __name__ == "__main__":
    main()

