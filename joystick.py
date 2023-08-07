#!/usr/bin/env python

from evdev import InputDevice, categorize, ecodes
import time, threading
from queue import PriorityQueue
import Adafruit_BBIO.GPIO as GPIO
import pydrs


LED = "P8_28"
PS_CH = 1
PS_CV = 2

UPPER_LIMIT = 10 # Amps
LOWER_LIMIT = -10 # Amps


class PS_JoystickControl():

    def __init__(self):
        self.gamepad = InputDevice('/dev/input/event1')

        # Parametro de Inicio - Botao e Sinalizacao
        self.init = False
        GPIO.setup(LED,GPIO.OUT)
        self.drs = pydrs.EthDRS("127.0.0.1",5000)
        self.drs.timeout = 5

        # Fila de Operacoes
        self.queue = PriorityQueue()

        # Threads
        self.Joystick = threading.Thread(target = self.ReadJoystick)
        self.Joystick.setDaemon(True)
        self.Joystick.start()

        self.Commands = threading.Thread(target = self.SendCommand)
        self.Commands.setDaemon(True)
        self.Commands.start()


    def ReadJoystick(self):
        for event in self.gamepad.read_loop():
            absevent = categorize(event)
            # Botao: Liga/Desliga Sistema
            if event.type == ecodes.EV_KEY:
                if (ecodes.bytype[absevent.event.type][absevent.event.code] == 'BTN_BASE' and absevent.event.value == 1):
                    self.init = not self.init
                    # LED and Configs
                    if (self.init):
                        print("Configuring PS and start manual controlling...")
                        try:
                            self.drs.slave_addr = PS_CH
                            self.drs.reset_interlocks()
                            self.drs.turn_on()

                            self.drs.slave_addr = PS_CV
                            self.drs.reset_interlocks()
                            self.drs.turn_on()

                            GPIO.output(LED,GPIO.HIGH)
                        except:
                            print("Timeout!")

                    else:
                        print("Turning off PS and disable manual controlling...")
                        try:
                            self.drs.slave_addr = PS_CH
                            self.drs.turn_off()

                            self.drs.slave_addr = PS_CV
                            self.drs.turn_off()
                            GPIO.output(LED,GPIO.LOW)
                        except:
                            print("Timeout!")


            # Analogicos
            elif (event.type == ecodes.EV_ABS and self.init == True):
                self.queue.put((1, [ecodes.bytype[absevent.event.type][absevent.event.code], absevent.event.value]))

    def SendCommand(self):
        while True:
	    # operation = [DIRECAO, VALOR]
            operation = self.queue.get(block = True)[1]

            if operation[0] == "ABS_X":
                current_value = UPPER_LIMIT * operation[1]/128 + LOWER_LIMIT
                print("X: ", str(current_value), " A")
                try:
                    self.drs.slave_addr = PS_CH
                    self.drs.set_slowref(current_value)
                except:
                    print("Timeout!")

            elif operation[0] == "ABS_Y":
                current_value = LOWER_LIMIT * operation[1]/128 + UPPER_LIMIT
                print("Y: ", str(current_value), " A")
                try:
                    self.drs.slave_addr = PS_CV
                    self.drs.set_slowref(current_value)
                except:
                    print("Timeout!")




print ("-----------------------------------------")
print ("----- Joystick Power Supply Control -----")
print ("-----------------------------------------")

PS_JoystickControl()

for _ in range(5):
    GPIO.output(LED,GPIO.HIGH)
    time.sleep(0.2)
    GPIO.output(LED,GPIO.LOW)
    time.sleep(0.2)

while True:
    time.sleep(10)
