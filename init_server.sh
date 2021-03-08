source env/bin/activate
lxterminal -e python3 serial_brain/test_socket.py &
sleep 3
python3 app.py &
