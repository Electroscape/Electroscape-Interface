from random import random
import json
from datetime import datetime as dt

# TODO:
# Test of the clean exit

rpi_env = True

'''
    don't ask, everything on the frontend get smeared into strings
    bool_dict = {"true": True, "false": False}
    bool_convert = {"True": "false", "Talse": "true"}
'''
bool_dict = {"on": True, "off": False}


class Settings:
    def __init__(self, room_name, master_reset, serial_limit):
        self.room_name = room_name
        # we may need and individual reset pin for each brain at some point
        self.master_reset = master_reset
        self.is_rpi_env = True
        self.serial_limit = serial_limit


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
        print(self)
        print("setting status for frontend for relay {}".format(self.name))
        if self.status:
            self.status_frontend = "On"
        else:
            self.status_frontend = "Off"

    def set_status(self, status):
        self.status = status
        if self.status:
            self.btn_clr_frontend = "green"
        else:
            self.btn_clr_frontend = "red"
        self.__set_frontend_status()

    def __init__(self, name, active_high, auto, hidden, brain_association, intput_pin, output_pin, index):
        self.name = name
        self.active_high = active_high
        self.auto = auto
        self.auto_frontend = "true"
        # this just is a function used to set the frontend to the same as backend,
        # just here to init the latter
        self.set_auto(self.auto)
        self.hidden = hidden
        self.brain_association = brain_association
        self.input = intput_pin
        self.output = output_pin
        self.status = False
        # since its going to be a pain in the ass on frontend even converting bools...
        self.btn_clr_frontend = 'green'
        self.set_status(self.status)
        self.index = index


class Brain:
    def __init__(self, name, relays, brain_no):
        self.name = name
        associated_relays = []
        for relay in relays:
            if relay.brain_association == brain_no + 1:
                associated_relays.append(relay)
        self.associated_relays = associated_relays


class STB:
    def __init__(self):
        self.updates = []
        self.serial_buffer = ["line1\n", "line2\n", "line3\n"]
        self.serial_updates = []
        self.settings, self.relays, self.brains = self.__load_stb()
        self.GPIO = self.__gpio_init()
        self.update_stb()
        self.user = False
        self.extended_relays = False
        print("stb init done")

    def __load_stb(self):
        try:
            with open('config.json') as json_file:
                cfg = json.loads(json_file.read())
                room_name = cfg["Room_name"]
                relays = cfg["Relays"]
                brains = cfg["Brains"]
                pins_IO = cfg["Pins_IO"]
                master_reset = cfg["Master_reset"]
                serial_limit = cfg["Serial_line_limit"]
        except ValueError as e:
            print('failure to read config.json')
            print(e)
            exit()

        for i, relay in enumerate(relays):
            relay_data = relay + pins_IO[i] + [i]
            relays[i] = Relay(*relay_data)

        for i, brain in enumerate(brains):
            brains[i] = Brain(brain, relays, i)

        settings = Settings(room_name, master_reset, serial_limit)
        return settings, relays, brains

    def __gpio_init(self):
        try:
            import RPi.GPIO as GPIO
            print("Running on RPi")
            GPIO.setmode(GPIO.BCM)
        except (RuntimeError, ModuleNotFoundError):
            print("Running without GPIOs on non Pi ENV / non RPi.GPIO installed machine")
            self.settings.self.is_rpi_env = False
            from fakeRPiGPIO import GPIO
        except OSError as e:
            print(e)
            print("sth went terribly wrong with GPIO import")
            exit()

        for relay in self.relays:
            if relay.active_high:
                pud = GPIO.PUD_DOWN
            else:
                pud = GPIO.PUD_UP
            GPIO.setup(relay.input, GPIO.IN, pull_up_down=pud)
            GPIO.setup(relay.output, GPIO.OUT, pull_up_down=pud)

        return GPIO

    def set_override(self, relay_index, value, test):
        # do yourself a favour and dont pass values into html merely JS,
        # converting bools into 3 different languages smeard into json is not fun
        print("testval: {}".format(test))
        relay = self.relays[int(relay_index)]
        '''
        try:
            value = not bool_dict[value]
            relay.auto = value
        except KeyError:
            print("KEYERROR!")
        '''
        relay.set_auto(not relay.auto)

    # changes form the frontend applied to the GPIO pins
    def set_relay(self, part_index, status=None, test=None):
        print("set_relay vars {} {} {}".format(part_index, status, test))
        relay = self.relays[part_index]
        # if we pass nothing we flip the relay
        if status is None or type(status) is not bool:
            status = not relay.status
        print("setting relay {} to status {}".format(part_index, status))
        relay.set_status(status)
        self.GPIO.output(relay.output, relay.status)

    def restart_brain(self, part_index, value, test):
        # Todo
        print("restart_brain is WIP till we get RS485 communication ")

    # *_ dumps unused variables
    def login(self, *args):
        user = args[1]
        print("loggig in user {}".format(user))
        self.user = user



    def extend_relays(self, *_):
        self.extended_relays = True

    def logout(self, *_):
        self.user = False
        self.extended_relays = False

    def __add_serial_lines(self, lines):
        for line in lines:
            # if we have problems with line termination for whatever reason we can edit them here
            self.serial_updates.insert(0, line)
            self.serial_buffer.insert(0, line)
            new_size = min(len(self.serial_buffer), self.settings.serial_limit)
            self.serial_buffer = self.serial_buffer[:new_size]

    # reads and updates the STB and sets/mirrors states
    def update_stb(self):
        print("update_stb")
        print("adding some random fake updates")
        
        for relay_no, relay in enumerate(self.relays):
            # auto = true, manual = false
            if relay.auto:
                # new_status = bool(self.GPIO.input(relay.input))
                new_status = bool(round(random()))
                print("mirroring relay {}".format(relay.index))
                self.GPIO.output(relay.output, relay.status)

                if new_status != relay.status:
                    relay.set_status(new_status)
                    self.updates.append([relay_no, relay.status_frontend, relay.btn_clr_frontend])
        self.__add_serial_lines([str(dt.now()) + "\n",
                                 "more lines\n", "and more\n"])


def cleanup(self):
    self.GPIO.cleanup()

# https://www.shanelynn.ie/asynchronous-updates-to-a-webpage-with-flask-and-socket-io/
# https://flask-socketio.readthedocs.io/en/latest/

# https://realpython.com/flask-by-example-implementing-a-redis-task-queue/

# https://docs.python.org/3/whatsnew/3.8.html#asyncio
# https://www.youtube.com/watch?v=LYTiaSXso_4
# start async first do async.run(fnc_name)
# run parallel?
# async.gather(fn1, fn2, fn3)


# just here fore testing when running stb.py, usually this is imported
if __name__ == "__main__":
    print("")






