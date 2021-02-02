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

from socketServer import SocketServer
import json

try:
    with open('serial_config.json') as json_file:
        cfg = json.loads(json_file.read())
        socket_port = cfg["serial_port"]
except ValueError as e:
    print('failure to read serial_config.json')
    print(e)
    exit()


def main():
    sock = SocketServer(socket_port)
    print("ready to send data to the frontend")
    while True:
        try:
            line = input("Send line: ")
            sock.transmit(line)
        except KeyboardInterrupt:
            # add sock.shutdown as fnc?
            exit()


main()



