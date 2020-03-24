# ###################################################################
# Ruben Cardenes -- Mar 2020
#
# File:        stream_video_client.py
# Description: This scripts starts a client in the Raspberry pi that connects
#              to a server in another PC. Upon connection, this scripts sends
#              a video stream from the PI camera encoded as JPEG
#              and listens for incoming commands to drive a car connected to the
#              Pi. In this case, the Pi connects to two motors in the car with a
#              L298N H-Bridge motor controller. There is a motor for
#              forward-backward movement and another for left-right steering.
#
# Note: the class L298N_HBridge_DC_Motor has been taken from the donkey-car project
#       and slightly modified
# ###################################################################

import io
import socket
import struct
import time
import picamera
import pickle
from threading import Thread
from argparse import ArgumentParser


def map_range(x, X_min, X_max, Y_min, Y_max):
    '''
    Linear mapping between two ranges of values
    '''
    X_range = X_max - X_min
    Y_range = Y_max - Y_min
    XY_ratio = X_range/Y_range

    y = ((x-X_min) / XY_ratio + Y_min) // 1

    return int(y)


class L298N_HBridge_DC_Motor(object):
    '''
    Motor controlled with an L298N hbridge from the gpio pins on Rpi
    '''

    def __init__(self, pin_forward, pin_backward, pwm_pin, freq=50, max_duty=90, min_value=0):
        import RPi.GPIO as GPIO
        self.pin_forward = pin_forward
        self.pin_backward = pin_backward
        self.pwm_pin = pwm_pin

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin_forward, GPIO.OUT)
        GPIO.setup(self.pin_backward, GPIO.OUT)
        GPIO.setup(self.pwm_pin, GPIO.OUT)

        self.pwm = GPIO.PWM(self.pwm_pin, freq)
        self.pwm.start(0)
        self.max_duty = max_duty
        self.min_value = min_value
        self.throttle = 0

    def run(self, speed):
        import RPi.GPIO as GPIO
        '''
        Update the speed of the motor where 1 is full forward and
        -1 is full backwards.
        '''
        if speed > 1 or speed < -1:
            raise ValueError("Speed must be between 1(forward) and -1(reverse)")

        self.speed = speed
        self.throttle = int(map_range(speed, -1, 1, -self.max_duty, self.max_duty))
        if self.throttle < self.min_value and self.min_value > 0:
            self.throttle = self.throttle + 10

        if self.throttle > 0:
            self.pwm.ChangeDutyCycle(self.throttle)
            GPIO.output(self.pin_forward, GPIO.HIGH)
            GPIO.output(self.pin_backward, GPIO.LOW)
        elif self.throttle < 0:
            self.pwm.ChangeDutyCycle(-self.throttle)
            GPIO.output(self.pin_forward, GPIO.LOW)
            GPIO.output(self.pin_backward, GPIO.HIGH)
        else:
            self.pwm.ChangeDutyCycle(self.throttle)
            GPIO.output(self.pin_forward, GPIO.LOW)
            GPIO.output(self.pin_backward, GPIO.LOW)

    def shutdown(self):
        import RPi.GPIO as GPIO
        self.pwm.stop()
        GPIO.cleanup()

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
        self.receive_controls = receive_controls
        HBRIDGE_PIN_LEFT  = 16
        HBRIDGE_PIN_RIGHT = 18

        HBRIDGE_PIN_FWD   = 11
        HBRIDGE_PIN_BWD   = 13

        HBRIDGE_EN_PW_LR  = 33
        HBRIDGE_EN_PW_FB  = 32

        print("Init of steering")
        self.steering = L298N_HBridge_DC_Motor(HBRIDGE_PIN_LEFT, HBRIDGE_PIN_RIGHT, HBRIDGE_EN_PW_LR, max_duty=80)
        print("Init of throttle")
        self.throttle = L298N_HBridge_DC_Motor(HBRIDGE_PIN_FWD, HBRIDGE_PIN_BWD, HBRIDGE_EN_PW_FB, max_duty=60, min_value=30)

    def run(self):
        try:
            with picamera.PiCamera() as camera:
                camera.resolution = (160, 120)  # pi camera resolution
                camera.framerate = 10  # 10 frames/sec
                time.sleep(2)  # give 2 secs for camera to initilize
                stream = io.BytesIO()

                # send jpeg format video stream
                for foo in camera.capture_continuous(stream, 'jpeg', use_video_port=True):
                    self.connection.write(struct.pack('<L', stream.tell()))
                    self.connection.flush()
                    stream.seek(0)
                    self.connection.write(stream.read())
                    stream.seek(0)
                    stream.truncate()

                    # Now receive the steering and throttle and run
                    if self.receive_controls:
                        message = self.client_socket.recv(64)
                        steering_val, throttle_val = map(float, message.decode().split(","))
                        print(f"{steering_val} {throttle_val}")
                        self.steering.run(steering_val)
                        self.throttle.run(throttle_val)

            # Pack zero as little endian unsigned long and send it to signal end of connection
            self.connection.write(struct.pack('<L', 0))

        finally:
            GPIO.cleanup()
            self.connection.close()
            self.client_socket.close()


class PS4ReceiveThread(Thread):
    # A class to receive data from PS4 using threads
    # This class inherits from Thread, which means that will run on a separate Thread
    # whenever called, it starts the run method

    def __init__(self, host, port):
        Thread.__init__(self)
        # create socket and bind host
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))
        self.HEADERSIZE = 10

    def run(self):
        try:
            new_msg = True
            full_msg = b''
            while True:
                ### Receiving Data
                data = self.client_socket.recv(512)
                if new_msg:
                    try:
                        msglen = int(data[:self.HEADERSIZE])
                        new_msg = False
                    except:
                        new_msg = True
                        continue

                full_msg += data
                if len(full_msg) - self.HEADERSIZE >= msglen:
                    # print("full msg recvd")
                    event = pickle.loads(full_msg[self.HEADERSIZE:])
                    # We set the new_msg flag to True
                    new_msg = True
                    # and reset the full message empty
                    full_msg = b''

                    print("Received event: ", event)

        finally:
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
                        default='192.168.1.3',
                        help='destination host name or ip',
                        required=False)
    args = vars(parser.parse_args())

    host = args['host']
    port = args['port']

    threads = []

    newthread = VideoSendThread(host, port,  receive_controls=args['receive_controls'])
    newthread.start()
    threads.append(newthread)

    PS4_command_reception = False
    if PS4_command_reception:
        newthread = PS4ReceiveThread(host, port)
        newthread.start()
        threads.append(newthread)

    for t in threads:
        t.join()

