# Author Martin Pek
# 2CP - TeamEscape - Engineering

import json
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

recv_sockets = []
logger_socket = None


def brain_restart_thread(gpio, reset_pins):
    for reset_pin in reset_pins:
        gpio.output(reset_pin, True)
    print("Restarting ...")
    sleep(0.5)
    for reset_pin in reset_pins:
        gpio.output(reset_pin, False)
    print("Done")


class Settings:
    def __init__(self, room_name, translation_dict, serial_limit, brain_tag):
        self.room_name = room_name
        self.is_rpi_env = True
        self.translation_dict = translation_dict
        self.serial_limit = serial_limit
        self.brain_tag = brain_tag


class Relay:

    def set_auto(self, auto):
        self.auto = auto

    def __set_frontend_status(self):
        if self.status == self.active_high:
            self.status_frontend = self.text_off
        else:
            self.status_frontend = self.text_on
        print("setting status for frontend for relay {} to {}".format(self.name, self.status_frontend))

    def set_status(self, status):
        self.status = status
        self.__set_frontend_status()

    def set_riddle_status(self, status):
        self.riddle_status = status

    def __init__(self, auto_index, **kwargs):
        relay_num = kwargs.get('relay_num', -1)
        assert (0 <= relay_num <= 7), "Relay number should be from 0 to 7"
        self.index = relay_num
        self.name = kwargs.get('name', "Extra")
        self.code = kwargs.get('code', "XX"+str(auto_index))
        self.active_high = kwargs.get('active_high', True)
        self.text_on = kwargs.get('text_on', "ON")
        self.text_off = kwargs.get('text_off', "OFF")
        self.answer = kwargs.get('answer', "N/A")
        self.auto_frontend = "true"
        # this just is a function used to set the frontend to the same as backend,
        # just here to init the latter
        self.hidden = kwargs.get('hidden', False)
        self.brain_association = kwargs.get('brain_num', -1)
        # statuses: [unsolved, done, correct, override or wrong]
        self.riddle_status = "unsolved"
        auto = kwargs.get('auto', True)
        # If not auto then no riddle is associated
        if type(auto) is not bool:
            self.status = (auto == "manual_high")
            auto = False
            self.riddle_status = "override"
        else:
            self.status = False
        self.auto = auto
        self.first_message = kwargs.get('first_message', "No Input")
        self.last_message = kwargs.get('first_message', "No Input")
        self.set_status(self.status)
        self.auto_default = self.auto


class Brain:
    def __init__(self, name, relays, brain_no, reset_pin):
        self.name = name
        associated_relays = []
        for relay in relays:
            if relay.brain_association == brain_no:
                associated_relays.append(relay.index)
        self.associated_relays = associated_relays
        self.reset_pin = reset_pin


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
            with open('example_cfgs/config 3DP.json') as json_file:
                cfg = json.loads(json_file.read())
                room_name = cfg["Room_name"]
                relays = cfg["Relays"]
                brains = cfg["Brains"]
                translation_dict = cfg["Translation_Dict"]
                serial_limit = cfg["Serial_line_limit"]
        except ValueError as e:
            print('failure to read config.json')
            print(e)
            exit()

        try:
            with open('serial_brain/serial_config.json') as json_file:
                cfg = json.loads(json_file.read())
                serial_port = cfg["serial_port"]
                test_port = cfg["test_port"]
                cmd_port = cfg["cmd_port"]
                brain_tag = cfg["brain_tag"]
        except ValueError as e:
            print('failure to read serial_config.json')
            print(e)
            exit()

        global recv_sockets, logger_socket
        # First socket Arduino on RS485, the next one is for injecting test strings from test_socket
        recv_sockets = [SocketClient('127.0.0.1', serial_port),
                        SocketClient('127.0.0.1', test_port, trials=5)]
        logger_socket = SocketServer(cmd_port)

        for i, relay in enumerate(relays):
            relays[i] = Relay(i, **relay)

        for i, brain_data in enumerate(brains):
            brain, reset_pin = brain_data
            brains[i] = Brain(brain, relays, i, reset_pin)

        settings = Settings(room_name, translation_dict,
                            serial_limit, brain_tag)
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
            pin = 7 - relay.index
            self.__read_pcf(relay)
            try:
                relay.set_status(self.pcf_write.port[pin])
            except IOError:
                self.error = "Error with write PCF"

    def __write_pcf(self, pin, value):
        try:
            self.pcf_write.port[pin] = value
        except IOError:
            self.error = "Error with write PCF"
            sleep(1)  # wait to avoid IO Error and try again
            self.__write_pcf(pin, value)

    def __read_pcf(self, relay, read_pcf_write=False):
        ret = relay.status
        pin = 7 - relay.index
        try:
            if read_pcf_write:
                ret = bool(self.pcf_write.port[pin])
            else:
                ret = bool(self.pcf_read.port[pin])
        except IOError:
            self.error = "Error with read PCF"
            sleep(1)  # wait to avoid IO Error and try again
            self.__read_pcf(relay, read_pcf_write)
        return ret

    def __gpio_init(self):
        try:
            import RPi.GPIO as GPIO
            print("Running on RPi")
        except (RuntimeError, ModuleNotFoundError):
            print("Running without GPIOs on non Pi ENV / non RPi.GPIO installed machine")
            self.settings.is_rpi_env = False
            # GPIO.VERBOSE = False
            from GPIOEmulator.EmulatorGUI import GPIO
        except OSError as e:
            print(e)
            print("sth went terribly wrong with GPIO import")
            exit()

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for brain in self.brains:
            GPIO.setup(brain.reset_pin, GPIO.OUT, initial=False)
        return GPIO

    # changes from the frontend applied to the GPIO pins
    def override_relay(self, relay_code, status=None, test=None):
        print("set_relay vars {} {} {}".format(relay_code, status, test))
        # Relay codes should be key parameter
        relay = [r for r in self.relays if r.code == relay_code][0]

        status = not relay.status
        print("setting relay {} to status {}".format(relay_code, status))
        self.__write_pcf(relay.index, status)
        relay.set_status(status)
        relay.set_riddle_status("override")

        # stop mirroring once override
        relay.set_auto(False)
        self.updates.insert(
            0, [relay.code, relay.status_frontend, relay.riddle_status])
        self.__log_action("User {} override relay {} to {}".format(
            self.user, relay.name, status))

        if relay.brain_association >= 0:
            try:
                logger_socket.transmit("!log: {}".format(
                    self.brains[relay.brain_association].name))
            except IndexError:
                print("\n Invalid brain association for relay {} {}".format(
                    relay.brain_association, relay.name))

    def restart_all_brains(self, *_):
        txt = "\n\nroom has been reset by user {}\n\n".format(self.user)
        print(txt)
        self.logout()
        logger_socket.transmit(txt)

        pins = []
        relays_to_reset = []

        for brain in self.brains:
            relays_to_reset += brain.associated_relays
            pins.append(brain.reset_pin)

        for relay_index in relays_to_reset:
            for relay in self.relays:
                if relay.index == relay_index:
                    relay.set_riddle_status("unsolved")
                    relay.set_auto(relay.auto_default)
                    relay.last_message = relay.first_message
                    break

        thread = Thread(target=brain_restart_thread, args=(self.GPIO, pins,))
        thread.start()

    def restart_brain(self, brain):
        pins = [brain.reset_pin]
        # brain.reset_relay_modes()
        thread = Thread(target=brain_restart_thread, args=(self.GPIO, pins,))
        thread.start()

    # Where is this used? so far unused
    def log_brain(self, part_index, *_):
        try:
            brain = self.brains[part_index]
            print("attempting to restart brain {}".format(brain.name))
            logger_socket.transmit("!log: {}".format(brain.name))
        except IndexError:
            print("Invalid brain selection on restart_brain: {}".format(part_index))

    # *_ dumps unused variables
    def login(self, *args):
        user = args[1]
        msg = "logging in user {}".format(user)
        print(msg)
        logger_socket.transmit("!login: {}".format(user))
        self.user = user

    def __log_action(self, message):
        self.__add_serial_lines([message])
        logger_socket.transmit("!RPi,action," + message + ",Done.")

    def set_admin_mode(self, *_):
        self.admin_mode = True

    def logout(self, *_):
        logger_socket.transmit("!logout: {} ".format(self.user))
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

    def __msg_translate(self, msg):
        result = ""
        for word in msg.split():
            try:
                word = self.settings.translation_dict[word]
            except KeyError:
                pass
            result = result + word + " "
        result = result.rstrip()
        return result

    # checks for keywords in messages that contain updates to riddles and passes it on
    def __filter(self, lines):

        for index, line in enumerate(lines):
            line = line.lstrip()

            # only evaluate complete messages
            if match(self.settings.brain_tag, line) is None:
                print("no braintag, discarding")
                continue
            if search("Done.*$", line) is None:
                print("incomplete message, discarding")
                continue

            try:
                _, source, msg, _ = split(",", line)
            except ValueError:
                print("incomplete message, discarding following {}".format(line))
                continue

            if match("sys", source.lower()) is not None:
                # Brain is alive (Update ON box in frontend)
                # TODO: currently does nothing finish feature @abdullah or discuss with me
                # Brain restarted
                if search("setup", msg.lower()):
                    # needs more info even tho its incomplete
                    print("A riddle should restart")
                    # source is sys!!
                    # relay = [r for r in self.relays if r.code == source][0]
                    # relay.riddle_status = "unsolved"
                    continue

            for relay in self.relays:
                if relay.riddle_status == "done" or relay.riddle_status == "override":
                    continue

                if relay.riddle_status == "correct":
                    relay.riddle_status = "done"
                    continue

                # We check the current status
                if match(relay.code, source) is None:
                    continue

                relay.riddle_status = "unsolved"
                self.riddles_updated = True

                # when message is empty put first message
                if not bool(msg):
                    msg = relay.first_message

                if match('!', msg) is None:
                    msg = self.__msg_translate(msg)
                    relay.last_message = msg
                    print("updating last_message to: {}".format(msg))
                    lines[index] = msg
                else:
                    msg = msg.lower()
                    if match('!reset', msg) is not None:
                        relay.last_message = relay.first_message
                    relay.riddle_status = msg[1:]
        return lines

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
                new_status = self.__read_pcf(relay)
                if new_status != relay.status:
                    relay.set_status(new_status)
                    relay_msg = "Relay {} switched to {} by Brain".format(
                        relay.code, relay.status)
                    if self.admin_mode or not relay.hidden:
                        self.__log_action(relay_msg)
                    else:
                        logger_socket.transmit(relay_msg)
                    self.updates.insert(
                        0, [relay.code, relay.status_frontend, relay.riddle_status])

                self.__write_pcf(relay.index, new_status)

        # self.__add_serial_lines(["counter is at {}".format(counter)])
        for recv_socket in recv_sockets:
            ser_lines = recv_socket.read_buffer()  # copy.deepcopy()
            if ser_lines is not None and ser_lines:
                print("received ser_lines: ")
                for line in ser_lines:
                    print(line)
                print("\n")
                ser_lines = self.__filter(ser_lines)  # basically a reverse
                ser_lines = ser_lines[::-1]
                # print("returned ser_lines: {}".format(ser_lines))
                self.__add_serial_lines(ser_lines)

    def cleanup(self):
        self.GPIO.cleanup()


# just here fore testing when running stb.py, usually this is imported
if __name__ == "__main__":
    print("")
