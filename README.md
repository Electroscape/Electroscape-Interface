# README

web_stb_override beta

## RPi setup

Setup a RPi with a static IP

Raspi-config
- enable I2C
- enable Serial Port (serial GPIO)

open `sudo nano /etc/modules` and append
>i2c-bcm2708    
>i2c-dev

to verify the I2C functioning correctly install     
>sudo apt-get install i2c-tools

and verify connection with the PCF8574 by checking addresses with. 
This may be done by connecting the RPi GPIOs directly to PCFs if troubleshooting requires it
>i2cdetect -y 1


## Software installation

This project uses a Venv, this is build and tested for RPis on Python 3.7.x 
versions earlier than 3.6 are not supported. 

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

The Venv doesnt contain GPIOEmulator simply install it and when the RPI.GPIO class is not detected
it will be used instead.
fakeRPiGPIO library is on conflict with the RPi GPIO library and breaks the Rpi.GPIO when simply present on the system
and has been ditched for this project

## notes

- checkboxes do submit an empty dict when set on true
- UWSGI.ini with enable-threads = true is crucial to get threading running,
    glad you found out now bec have fun finding that information
- FLASK_ENV=development flask run
- FLASK_ENV=production flask run
- since browsers do not update stylesheets you need to manually reload those button combo may be ctrl-shift-r
- glob is a standard python library and may only be needed to be installed on RPi, handle manually if needed
