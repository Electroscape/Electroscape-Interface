# Author Martin Pek & Abdullah Saei
# 2CP - TeamEscape - Engineering

# The purpose of this script is to give a socket that can be used to test the frontend by feeding it tagged lines
# Frame examples: for copy and paste
# !BrLight,LIT,123,Done.
# !BrCUBE,UVL,C1 __ C2,Done.
# !BrLight,LIT,!Correct,Done.
# !BrAny,HID,!Wrong,Done.
# !BrLight,LIT,!Reset,Done.
# !BrCUBE,SYS,refresh,Done.
# !BrLight,SYS,Setup done,Done.
# !BrCUBE,UVL,translate_this translate_this,Done.

# !BrLight,LIT,!Correct,Done.
# !BrLight,LIT,1234,Done.
# !BrLight,LIT,4321,Done.\n!BrLight,LIT,!Wrong,Done.
# !BrLight,LIT,4321,Done.\n!BrLight,LIT,!Reset,Done.

# !Br,XX3,!correct,Done.
# !Br,XX4,!wrong,Done.

from socketServer import SocketServer
from pathlib import Path
import json


for file_name in ['serial_brain/serial_config.json', 'serial_config.json']:
    if Path(file_name).is_file():
        try:
            with open(file_name) as json_file:
                cfg = json.loads(json_file.read())
                socket_port = cfg["test_port"]
        except ValueError as e:
            print('failure to read serial_config.json')
            print(e)
            exit()


def main():
    sock = SocketServer(socket_port)
    print("ready to send data to the frontend")
    while True:
        try:
            # seems to be a perculiarity of string literals could do \\n -> \n aswell
            lines = input("Send line: ").replace(r'\n', '\n')
            for line in lines.splitlines():
                print("sending line: {}".format(line))
                sock.transmit(line)
        except KeyboardInterrupt:
            # add sock.shutdown as fnc?
            exit()


main()
