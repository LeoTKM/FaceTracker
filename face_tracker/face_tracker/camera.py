# @brief Computer vision, publishing changes (in pixels) in the centre of the face in both the x, y directions 
# Modified FPS to 30 and halved frame sizes to reduce latency
#
# @author Leo
#
# Contact leowang657@gmail.com

# -- ROS2 -- 
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
import threading

# -- Message types -- 
from std_msgs.msg import String 
from face_messages.msg import FaceShift 

import logging
import cv2 as cv
import numpy as numpy
import time

SHIFT_TOLERANCE = 22  
faceCascade = cv.CascadeClassifier('haarcascade_frontalface_default.xml')

class Camera(Node):
    def __init__(self):
        super().__init__('camera')
        self.publisher_ = self.create_publisher(FaceShift, '/camera_data', 10)

        # the FaceShift message type contains the change (in pixels) in x, change in y and init_done: bool
        self.init_done: bool = False
        self.delta_x: int = 0 # px
        self.delta_y: int = 0 # px
        self.lock = threading.Lock()

        self.camera_index = None
        
        for i in range(0, 15):
            cam = cv.VideoCapture(i)
            if cam.isOpened():
                self.camera_index = i
        
        if (not self.camera_index):
            self.get_logger().error("Check camera connection")
            return 

        print("Found camera")
        self.init_done = True

        self.cam = cv.VideoCapture(self.camera_index)
        self.cam.set(cv.CAP_PROP_FPS, 30)

        frame_width = int(self.cam.get(cv.CAP_PROP_FRAME_WIDTH)) / 2        # Frame resized to half its original size
        frame_height = int(self.cam.get(cv.CAP_PROP_FRAME_HEIGHT)) / 2

        self.half_frame_width = frame_width / 2
        self.half_frame_height = frame_height / 2

        # the publish_centre_shift method is called every 10 ms,
        # which means it is called approximately three times per camera frame,
        # increasing reliability since the camera runs at 30 FPS.
        self.publish_group = MutuallyExclusiveCallbackGroup()
        self.timer = self.create_timer(0.01, self.publish_centre_shift, callback_group = self.publish_group)

        # the camera captures each frame and runs the face detection algorithm continously 
        # and independently of the publishing process (therefore we need multithread)
        # therefore we need multithread to prevent publish_centre_shift & camera_collection from running in the same thread
        self.camera_thread = threading.Thread(target=self.camera_collection, daemon=True)
        self.camera_thread.start()


    def camera_collection(self) -> None:
        rval, frame = self.cam.read()

        while rval:
            rval, frame = self.cam.read()

            # resize (1/2)
            scale_factor_x = 0.5
            scale_factor_y = 0.5
            resized_frame = cv.resize(frame, None, fx=scale_factor_x, fy=scale_factor_y, interpolation=cv.INTER_AREA)

            self.detect_face(resized_frame)
            key = cv.waitKey(1)
            if key == 27:
                break
            self.cam.release()


    def detect_face(self, img):
        face_img = img.copy()
        face_rect = faceCascade.detectMultiScale(face_img, scaleFactor=1.3, minNeighbors=5)
        # face_rect is a tuple, ie (x, y, w, h), (x, y) is the top left corner of the face

        if (face_rect):
            face_centre_x = int(x + w/2)
            face_centre_y = int(y + h/2)

            with self.lock:
            # if delta_x = 0 -> shift is insignificant
                delta = face_centre_x - self.half_frame_width
                self.delta_x = (delta) if delta > (SHIFT_TOLERANCE) else 0

                delta = face_centre_y - self.half_frame_height
                self.delta_y = (delta) if delta > (SHIFT_TOLERANCE) else 0     


    def publish_centre_shift(self):
        # the FaceShift message type contains the change in x, change in y and init_done: bool
        msg = FaceShift()
        with self.lock:
            msg.delta_x = self.delta_x
            msg.delta_y = self.delta_y
        msg.init_done = self.init_done
        
        self.publisher_.publish(msg)
        

def main(args=None):
    rclpy.init(args=args)

    camera = Camera() 
    executor = MultiThreadedExecutor() # mutli thread needed
    executor.add_node(camera)
    executor.spin()

    rclpy.shutdown()


if __name__ == "__main__":
    main()
