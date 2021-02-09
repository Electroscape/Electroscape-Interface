
# GPIOEmulator

The easiest way to use this package is to install using pip for python 2.7

```bash
$ sudo pip install GPIOEmulator
```

using pip3 for python 3

```bash
$ sudo pip3 install GPIOEmulator
```

To use the emulator just type the following at the beginning of your script.

```python
from GPIOEmulator.EmulatorGUI import GPIO
```

## Works with

- [python 2.7.15+](https://www.python.org/downloads/release/python-2715/)
- [python 3.6.8](https://www.python.org/downloads/release/3.6.8)

## Simulation

This library simulates the following functions which are used in the RPi.GPIO library.

- GPIO.setmode()
- GPIO.setwarnings()
- GPIO.setup()
- GPIO.input()
- GPIO.output()


