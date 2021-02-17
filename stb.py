# Author Martin Pek
# 2CP - TeamEscape - Engineering

# from random import random
import json
# from datetime import datetime as dt
from serial_brain.socket_client import SocketClient
from serial_brain.socketServer import SocketServer
from time import sleep
from threading import Thread
from re import split, match, search

# TODO:
'''
log receiving relay actions as well
- Except PCF with not for an override
    raise IOError(ffi.errno)
    OSError: 121
    its caused by disconnected or malfunctioning PCF hardware -> 
    link to instructions to ???
- self.sock.bind(("127.0.0.1", port))
    OSError: [Errno 98]
    Address already in use
    either with reset protocol or socket shutdown when script is turned off/crashes
    or timeout?
'''

rpi_env = True

'''
    don't ask, everything on the frontend get smeared into strings
    bool_dict = {"true": True, "false": False}
    bool_convert = {"True": "false", "False": "true"}
'''
bool_dict = {"on": True, "off": False}
serial_socket = None
cmd_socket = None
# counter = 0


# if the threading here doesn't work move it to app into the updater thread
def brain_restart_thread(gpio, reset_pins):
    for reset_pin in reset_pins:
        gpio.output(reset_pin, True)
    print("Restarting ...")
    sleep(0.5)
    for reset_pin in reset_pins:
        gpio.output(reset_pin, False)
    print("Done")


class Settings:
    def __init__(self, room_name, serial_limit, brain_tag):
        self.room_name = room_name
        self.is_rpi_env = True
        self.serial_limit = serial_limit
        self.brain_tag = brain_tag


class Relay:

    def __set_frontend_auto(self):
        # since the label is Auto for the checkbox its reverse
        if self.auto:
            self.auto_frontend = "true"
        else:
            self.auto_frontend = "false"

    def set_auto(self, auto):
        self.auto = auto
        self.__set_frontend_auto()

    def __set_frontend_status(self):
        print("setting status for frontend for relay {}".format(self.name))
        if self.status:
            self.status_frontend = self.text_on
        else:
            self.status_frontend = self.text_off

    def set_status(self, status):
        self.status = status
        self.__set_frontend_status()

    def __init__(self, index, **kwargs):
        self.relay_no = kwargs.get('relay_num', -1)
        # Relay number is essential parameter
        assert (0 <= self.relay_no <= 7) , "Relay number should be from 0 to 7"
        self.name = kwargs.get('name', "Extra")
        self.code = kwargs.get('code', "XX"+str(index))
        self.active_high = kwargs.get('active_high', True)
        self.auto = kwargs.get('auto', True)
        self.text_on = kwargs.get('text_on', "ON")
        self.text_off = kwargs.get('text_off', "OFF")
        self.auto_frontend = "true"
        # this just is a function used to set the frontend to the same as backend,
        # just here to init the latter
        self.set_auto(self.auto)
        self.hidden = kwargs.get('hidden', False)
        self.brain_association = kwargs.get('brain_association', -1)
        self.status = False
        self.first_message = kwargs.get('first_message', "No Input")
        self.last_message = kwargs.get('first_message', "No Input")
        # unsolved, done, correct or wrong
        self.riddle_status = "unsolved"
        self.set_status(self.status)
        self.index = index
        self.auto_default = self.auto


class Brain:
    def __init__(self, name, relays, brain_no, reset_pin):
        self.name = name
        associated_relays = []
        for relay in relays:
            if relay.brain_association == brain_no + 1:
                associated_relays.append(relay)
        self.associated_relays = associated_relays
        self.reset_pin = reset_pin

    def reset_relay_modes(self):
        for relay in self.associated_relays:
            relay.set_auto(relay.auto_default)


class STB:
    def __init__(self):
        self.updates = []
        self.serial_buffer = ["line1\n", "line2\n", "line3\n"]
        self.serial_updates = []
        self.settings, self.relays, self.brains = self.__load_stb()
        self.GPIO = self.__gpio_init()
        self.__pcf_init()
        self.user = False
        self.admin_mode = False
        self.error = False
        self.riddles_updated = True     # Start with true to update frontend
        self.update_stb()
        print("stb init done")

    def __load_stb(self):
        try:
            with open('config.json') as json_file:
                cfg = json.loads(json_file.read())
                room_name = cfg["Room_name"]
                relays = cfg["Relays"]
                brains = cfg["Brains"]
                serial_limit = cfg["Serial_line_limit"]
        except ValueError as e:
            print('failure to read config.json')
            print(e)
            exit()

        try:
            with open('serial_brain/serial_config.json') as json_file:
                cfg = json.loads(json_file.read())
                serial_port = cfg["serial_port"]
                cmd_port = cfg["cmd_port"]
                brain_tag = cfg["brain_tag"]
        except ValueError as e:
            print('failure to read serial_config.json')
            print(e)
            exit()

        global serial_socket, cmd_socket
        serial_socket = SocketClient('127.0.0.1', serial_port)
        cmd_socket = SocketServer(cmd_port)

        for i, relay in enumerate(relays):
            relays[i] = Relay(i, **relay)

        for i, brain_data in enumerate(brains):
            brain, reset_pin = brain_data
            brains[i] = Brain(brain, relays, i, reset_pin)

        settings = Settings(room_name, serial_limit, brain_tag)
        return settings, relays, brains

    def __pcf_init(self):
        if self.settings.is_rpi_env:
            from pcf8574 import PCF8574
        else:
            from PCF_dummy import PCF8574

        self.pcf_read = PCF8574(1, 0x38)
        self.pcf_write = PCF8574(1, 0x3f)
        # since the creating the instances does fail silently let's check
        # Get pin value from relay_no attr in relay instance
        for relay in self.relays:
            pin = relay.relay_no
            self.__read_pcf(pin)
            try:
                self.pcf_write.port[pin]
            except IOError:
                self.error = "Error with write PCF"

    def __write_pcf(self, pin, value):
        try:
            self.pcf_write.port[pin] = value
        except IOError:
            self.error = "Error with write PCF"

    def __read_pcf(self, pin):
        ret = self.relays[pin].status
        try:
            ret = bool(self.pcf_read.port[pin])
        except IOError:
            self.error = "Error with write PCF"
        return ret

    def __gpio_init(self):
        try:
            import RPi.GPIO as GPIO
            print("Running on RPi")
        except (RuntimeError, ModuleNotFoundError):
            print("Running without GPIOs on non Pi ENV / non RPi.GPIO installed machine")
            self.settings.is_rpi_env = False
            # from fakeRPiGPIO import GPIO
            # GPIO.VERBOSE = False
            from GPIOEmulator.EmulatorGUI import GPIO
        except OSError as e:
            print(e)
            print("sth went terribly wrong with GPIO import")
            exit()

        GPIO.setmode(GPIO.BCM)
        for brain in self.brains:
            GPIO.setup(brain.reset_pin, GPIO.OUT, initial=False)
        return GPIO

    def set_override(self, relay_index, value, test):
        # do yourself a favour and don't pass values into html merely JS,
        # converting bools into 3 different languages smeared into json is not fun
        # function only flips existing variable
        relay = self.relays[int(relay_index)]
        relay.set_auto(not relay.auto)
        self.__log_action("{} relay {} auto {}".format(
            self.user, relay.index, relay.auto))

    # changes from the frontend applied to the GPIO pins
    def set_relay(self, part_index, status=None, test=None):
        print("set_relay vars {} {} {}".format(part_index, status, test))
        relay = self.relays[part_index]
        # if we pass nothing we flip the relay
        if status is None or type(status) is not bool:
            status = not relay.status
        print("setting relay {} to status {}".format(part_index, status))
        relay.set_status(status)
        self.__write_pcf(relay.relay_no, relay.status)
        self.__log_action("User {} Relay {} from {} to {}".format(
            self.user, relay.name, not status, status))
        # takes the cake for the unsexiest variable
        cmd_socket.transmit("!log: {}".format(
            self.brains[relay.brain_association].name))

    def restart_all_brains(self, *_):
        txt = "\n\nroom has been reset by user {}\n\n".format(self.user)
        print(txt)
        cmd_socket.transmit(txt)

        pins = []
        for brain in self.brains:
            for relay in brain.associated_relays:
                relay.last_message_status = relay.first_message
            brain.reset_relay_modes()
            pins.append(brain.reset_pin)
        thread = Thread(target=brain_restart_thread, args=(self.GPIO, pins,))
        thread.start()

    def restart_brain(self, brain):
        pins = [brain.reset_pin]
        brain.reset_relay_modes()
        for relay in brain.associated_relays:
            relay.last_message_status = relay.first_message
        thread = Thread(target=brain_restart_thread, args=(self.GPIO, pins,))
        thread.start()

    def log_brain(self, part_index, *_):
        try:
            brain = self.brains[part_index]
            print("attempting to restart brain {}".format(brain.name))
            cmd_socket.transmit("!log: {}".format(brain.name))
        except IndexError:
            print("Invalid brain selection on restart_brain: {}".format(part_index))

        print()

    # *_ dumps unused variables
    def login(self, *args):
        user = args[1]
        msg = "logging in user {}".format(user)
        print(msg)
        cmd_socket.transmit("!login: {}".format(user))
        self.user = user

    def __log_action(self, message):
        self.__add_serial_lines([message])
        cmd_socket.transmit("!RPi,action," + message + ",Done.")

    def set_admin_mode(self, *_):
        self.admin_mode = True

    def logout(self, *_):
        cmd_socket.transmit("!logout: {} ".format(self.user))
        self.user = False
        self.admin_mode = False

    def relays_to_dict(self):   # Extract useful info from nested classes
        data = []
        for rel in self.relays:
            data.append({
                "code": rel.code,
                "riddle_status": rel.riddle_status,
                "last_message": rel.last_message
            })
        return data
    '''
    # question is if we need to create a separate thread or handle pausing differently
    # need to check likely we need to consider flasks limitations
    def reset_brains(self, brains):
        for brain in brains:
            self.GPIO.output(brain.reset_pin, True)

        sleep(0.5)
        for brain in brains:
            self.GPIO.output(brain.reset_pin, False)
    '''

    # checks for keyworded messaged that contain updates to riddles and passes it on
    def __filter(self, lines):
        for line in lines:
            # only evaluate complete messages
            if match(self.settings.brain_tag, line) is None:
                continue
            if search("Done.*$", line) is None:
                continue
            try:
                brain_name, source, msg, _ = split(",", line)
            except ValueError:
                print("incomplete message, discarding following {}".format(line))
                continue
            if match("sys", source.lower()) is not None:
                # Brain is alive (Update ON box in frontend)
                _ = brain_name
                continue

            for relay in self.relays:
                if match(relay.code, source) is None:
                    continue

                # if the riddle has been solved we no longer track it
                if relay.riddle_status == "done":
                    continue

                # if the riddle has been solved we no longer track it
                if relay.riddle_status == "correct":
                    relay.riddle_status = "done"
                    continue

                relay.last_message = msg
                relay.riddle_status = "unsolved"
                self.riddles_updated = True
                if match('!', msg) is None:
                    # if the password is reset on the arduino
                    if msg.lower() == '!reset':
                        relay.last_message = relay.first_message
                    # if !correct or !wrong
                    else:
                        relay.riddle_status = msg.lower()[1:]

    def __add_serial_lines(self, lines):
        for line in lines:
            # if we have problems with line termination for whatever reason we can edit them here
            self.serial_updates.insert(0, line)
            self.serial_buffer.insert(0, line)
            new_size = min(len(self.serial_buffer), self.settings.serial_limit)
            self.serial_buffer = self.serial_buffer[:new_size]

    # reads and updates the STB and sets/mirrors states
    def update_stb(self):
        for relay in self.relays:
            # auto = true, manual = false
            if relay.auto:
                new_status = self.__read_pcf(relay.relay_no)
                if new_status != relay.status:
                    relay.set_status(new_status)
                    relay_msg = "Relay {} switched to {} by Brain".format(
                        relay.code, relay.status)
                    if self.admin_mode or not relay.hidden:
                        self.__log_action(relay_msg)
                    else:
                        cmd_socket.transmit(relay_msg)
                    self.updates.insert(
                        0, [relay.relay_no, relay.status_frontend, relay.riddle_status])
                self.__write_pcf(relay.relay_no, new_status)

        # self.__add_serial_lines(["counter is at {}".format(counter)])
        ser_lines = serial_socket.read_buffer()
        if ser_lines is not None:
            ser_lines = reversed(ser_lines)
            self.__filter(ser_lines)
            self.__add_serial_lines(ser_lines)

    def cleanup(self):
        self.GPIO.cleanup()

# https://www.shanelynn.ie/asynchronous-updates-to-a-webpage-with-flask-and-socket-io/
# https://flask-socketio.readthedocs.io/en/latest/
# following didn't work iirc
# https://realpython.com/flask-by-example-implementing-a-redis-task-queue/


# just here fore testing when running stb.py, usually this is imported
if __name__ == "__main__":
    print("")
