# ###################################################################
# Ruben Cardenes -- Mar 2020
#
# File:        stream_video_server.py
# Description: This script starts a server that listen from incoming video streaming
#              connection (for instance from a Raspberry Pi), shows the video and
#              then depending on the mode it does:
#                  autopilot mode: process the frames with a keras model, and sends back to
#                          the Raspberry Pi the throttle and steering values for autonomous
#                          driving
#                  manual mode: interprets PS4 controller commands and sends them to the
#                          client as steering and throttle to control a remote car
#               Note: in manual mode, the PS4 and the video reception are processed in two
#               different threads
# ###################################################################

import cv2
import os
import numpy as np
from threading import Thread
import socket
from argparse import ArgumentParser
from PS4Controller import PS4Controller
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from keras_pilot import KerasCategorical


class VideoClientThread(Thread):
    """Class to Receive video data from client"""

    def __init__(self, ip, port, connection, model_path='', send_ps4=False):
        from keras_pilot import KerasLinear
        Thread.__init__(self)
        self.ip = ip
        self.port = port
        self.connection = connection
        self.model = None
        self.ps4 = None
        if send_ps4:
            self.ps4 = PS4Controller()
            self.ps4_events = self.ps4.generate_event()


        if model_path != '':
            IMAGE_W = 160
            IMAGE_H = 120
            input_shape = (IMAGE_H, IMAGE_W, 3)
            roi_crop = (0, 0)
            # self.model = KerasLinear(input_shape=input_shape, roi_crop=roi_crop)
            # Categorical model seems to work better
            self.model = KerasCategorical(input_shape=input_shape, roi_crop=roi_crop)
            self.model.load(model_path)
        print("[+] New server socket thread started for " + ip + ":" + str(port))

    def run(self):
        stream_bytes = b' '
        cv2.namedWindow("video feed", cv2.WINDOW_KEEPRATIO)

        # stream video frames one by one
        try:
            print("Video thread started")
            frame_num = 0
            i = 0
            while True:
                i += 1
                stream_bytes += self.connection.recv(1024)
                first = stream_bytes.find(b'\xff\xd8')
                last = stream_bytes.find(b'\xff\xd9')
                if first != -1 and last != -1:
                    jpg = stream_bytes[first:last + 2]
                    stream_bytes = stream_bytes[last + 2:]
                    image = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                    frame_num += 1
                    cv2.imshow("video feed", image)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                    if self.model is not None:
                        print(f"im shape {image.shape} {image.dtype}")
                        steering, throttle = self.model.run(image)
                        print(f"steering {steering} throtle {throttle}")
                        message = f'{steering}, {throttle}'
                        self.connection.send(message.encode())
                    if self.ps4 is not None:
                        os.system('clear')
                        steering, throttle = next(self.ps4_events)
                        print(f"steering {steering} throttle {throttle}")
                        message = f'{steering}, {throttle}'
                        self.connection.send(message.encode())

            cv2.destroyAllWindows()

        finally:
            self.connection.close()
            print("Connection closed on thread 1")


def start_multihreaded_server(server_host, port, model_path="", PS4_server=False):

    TCP_IP = server_host
    TCP_PORT = port

    tcpServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcpServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcpServer.bind((TCP_IP, TCP_PORT))
    threads = []

    # Video connection
    tcpServer.listen(4)
    print("Python server : Waiting for Video connection from TCP clients...")
    (conn, (ip, port)) = tcpServer.accept()
    newthread = VideoClientThread(ip, port, conn, model_path=model_path, send_ps4=PS4_server)
    newthread.start()
    threads.append(newthread)

    for t in threads:
        t.join()


if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument('--mode', type=str,
                        dest='mode',
                        default='video-only',
                        choices=['autopilot',  'manual', 'video-only'],
                        help='execution mode: (autopilot | manual | video-only)',
                        required=False)
    parser.add_argument('--port', type=int,
                        dest='port',
                        default=8887,
                        help='socket port',
                        required=False)
    parser.add_argument('--host', type=str,
                        dest='host',
                        default='0.0.0.0',
                        help='destination host name or ip',
                        required=False)
    args = vars(parser.parse_args())

    server_host = args['host']
    port = args['port']

    if args['mode'] == "autopilot":
        model_path = './models/pilot_home_day_cat_aug.h5'
        start_multihreaded_server(server_host, port, model_path=model_path, PS4_server=False)
    if args['mode'] == "manual":
        start_multihreaded_server(server_host, port, model_path="", PS4_server=True)
    if args['mode'] == "video-only":
        start_multihreaded_server(server_host, port, model_path="", PS4_server=False)
