# README

web_stb_override beta

## installation

Since flask can defenitely get issues like the latter one
use a Venv, this is build and tested for RPis on Python 3.7.x earlier version like 3.5x are not supported

simply update the venv location in env/bin/activate
line 40 VIRTUAL_ENV="/home/pi/TE/Electroscape-Interface/env"
to whatever is local to you

project contains shellscripts to launch from,
those can be made executeable with chmod +x myfile

alternatively from plain console
python3 -m venv env
and run the python files

## common inssues

### Socket-IO

ImportError: No module named socketio

 -> Delete the VEnv is 99% the culprit

[https://github.com/miguelgrinberg/Flask-SocketIO/issues/164]
[https://github.com/miguelgrinberg/Flask-SocketIO/issues/1105]
another issue that existed but got fixed by the provided requirements, pinning the Werkzeug==0.16.1
[https://github.com/jarus/flask-testing/issues/143]

- further Import errors like flask socketio:
do not run from Sudo python3 app.py, using sends you back to global env

- No serial found:
Make sure your RPi has serial console enabled but UART/BT disabled

## for development on a PC

- The Venv deliberately doesnt contain fakeRPiGPIO since this library is on conflict with the RPi GPIO library.
    therefore you should install it manually when working on a PC

## notes

- checkboxes do submit an empty dict when set on true
- UWSGI.ini with enable-threads = true is crucial to get threading running,
    glad you found out now bec have fun finding that information
- FLASK_ENV=development flask run
- FLASK_ENV=production flask run
- since browsers do not update stylesheets you may get frustrated till you find the manual reload button combo ctrl-shift-r
- glob is a standard python library and may only be needed to be installed on RPi, handle manually if needed
