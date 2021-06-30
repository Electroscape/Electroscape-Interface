import pickle
import sys
from time import sleep

import subprocess
rs485_socket = subprocess.Popen([sys.executable, "serial_brain/rs485_socket_server.py"])
# rs485_socket.kill()

keyword = '!wrong'
print(keyword[1:])

msg = "asdf\n"
msg_buffer = ""

msg_buffer = msg.rstrip() + "\n\n \n\n" + msg.rstrip()


for line in msg_buffer.split():
    print(line)

sleep(10)
print("end")