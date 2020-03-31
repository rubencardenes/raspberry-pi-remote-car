# ###################################################################
# Ruben Cardenes -- Mar 2020
#
# File:        PS4ControllerServer.py
#
# ###################################################################

import pygame
import pprint
import sys


class PS4Controller(object):
    """Class representing the PS4 controller"""

    controller = None
    axis_data = None
    button_data = None
    hat_data = None

    def __init__(self, verbose=False):
        """Initialize the joystick components"""

        pygame.init()
        pygame.joystick.init()
        self.controller = pygame.joystick.Joystick(0)
        self.controller.init()
        self.event_dict = {}
        self.axis_data = {i: 0 for i in range(7)}
        self.verbose = verbose
        self.steering, self.throttle = 0, 0
        if not self.axis_data:
            self.axis_data = {}

        if not self.button_data:
            self.button_data = {}
            for i in range(self.controller.get_numbuttons()):
                self.button_data[i] = False

        if not self.hat_data:
            self.hat_data = {}
            for i in range(self.controller.get_numhats()):
                self.hat_data[i] = (0, 0)

    def convert_dict_into_steer_throttle(self, event_dict):
        if sys.platform == 'linux':
            steering = event_dict['axis'][3]
            throttle = event_dict['axis'][1]
        else:
            steering = event_dict['axis'][2]
            throttle = event_dict['axis'][1]
        return steering, throttle

    def generate_event(self):
        """Listen for events to happen and send commands"""
        print("Generating event")
        hadEvent = False

        while True:

            for event in pygame.event.get():
                if event.type == pygame.JOYAXISMOTION:
                    self.axis_data[event.axis] = round(event.value, 2)
                elif event.type == pygame.JOYBUTTONDOWN:
                    self.button_data[event.button] = True
                elif event.type == pygame.JOYBUTTONUP:
                    self.button_data[event.button] = False
                elif event.type == pygame.JOYHATMOTION:
                    self.hat_data[event.hat] = event.value

                if event.type == pygame.JOYBUTTONDOWN:
                    # A button on the joystick just got pushed down
                    hadEvent = True
                elif event.type == pygame.JOYAXISMOTION:
                    # A joystick has been moved
                    hadEvent = True

                if hadEvent:
                    self.event_dict['axis'] = self.axis_data
                    self.event_dict['button'] = self.button_data

                    # if self.button_data[4]:
                    #    self.verbose = not self.verbose

                    if self.verbose:
                        # print("Button ")
                        # pprint.pprint(self.button_data)
                        print("Axis ")
                        pprint.pprint(self.axis_data)
                        # print("Motion ")
                        # pprint.pprint(self.hat_data)

                    self.steering, self.throttle = self.convert_dict_into_steer_throttle(self.event_dict)

            print("Generating ", self.steering, self.throttle)
            yield [self.steering, self.throttle]

