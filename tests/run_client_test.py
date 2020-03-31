# ###################################################################
# Ruben Cardenes -- Mar 2020
#
# File:        stream_video_client_test.py
# Description: This script is used for testing the client-server setup on the PC
#              It opens a connection in localhost and sends video streaming
#              from the USB camera
#
# ###################################################################

import io
import socket
import struct
import time
# import picamera
import cv2
from threading import Thread
from argparse import ArgumentParser
import pickle

# Video Sending Thread
class VideoSendThread(Thread):
    # A class to send video frames using threads
    # This class inherits from Thread, which means that will run on a separate Thread
    # whenever called, it starts the run method

    def __init__(self, host, port, receive_controls=False):
        Thread.__init__(self)
        # create socket and bind host
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))
        self.connection = self.client_socket.makefile('wb')
        self.IMAGE_W = 160
        self.IMAGE_H = 120
        self.receive_controls = receive_controls

    def run(self):
        try:
            start = time.time()
            message = b''
            stream = io.BytesIO()
            cap = cv2.VideoCapture(0)
            frame_count = 0
            while True:
                # send jpeg format video stream
                # encode the frame in JPEG format
                ret, frame = cap.read()
                frame = cv2.resize(frame, (self.IMAGE_W, self.IMAGE_H), cv2.INTER_AREA)
                (flag, encodedImage) = cv2.imencode(".jpg", frame)
                # ensure the frame was successfully encoded
                if not flag:
                    continue
                # change the output frame in the byte format
                encodedImage_byte = b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(
                    encodedImage) + b'\r\n'
                self.connection.write(encodedImage_byte)
                self.connection.flush()
                stream.seek(0)
                self.connection.write(stream.read())
                stream.seek(0)
                stream.truncate()

                # Receive the steering and throttle
                if self.receive_controls:
                    message = self.client_socket.recv(64)
                    steering, throttle = map(float, message.decode().split(","))
                    print(f"{steering} {throttle}")

            # Pack zero as little endian unsigned long and send it to signal end of connection
            self.connection.write(struct.pack('<L', 0))
        finally:
            self.connection.close()
            self.client_socket.close()

if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument('--receive_controls',
                        dest='receive_controls',
                        action='store_const', const=True,
                        default=False,
                        help='Defines if we are prepared to receive data from the server',
                        required=False)
    parser.add_argument('--port', type=int,
                        dest='port',
                        default=8887,
                        help='socket port',
                        required=False)
    parser.add_argument('--host', type=str,
                        dest='host',
                        default='localhost',
                        help='destination host name or ip',
                        required=False)
    args = vars(parser.parse_args())

    port = args['port']
    host = args['host']
    print(f"Connection to {host} {port}")
    print(f"Receive controls: {args['receive_controls']}")
    print(f"Press q to quit")

    threads = []

    newthread = VideoSendThread(host, port, receive_controls=args['receive_controls'])
    newthread.start()
    threads.append(newthread)

    for t in threads:
        t.join()
