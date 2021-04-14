# Author Martin Pek
# 2CP - TeamEscape - Engineering

from time import sleep
# Controls the relay that has been connected over PCF8574 (I2C) to the RPi

from pcf8574 import PCF8574

tester_address = 0x38
# device under test
dut_address = 0x39

# port is 1 for any but very first models of RPi
tester_pcf = PCF8574(1, tester_address)
dut = PCF8574(1, dut_address)


def scan():
    addresses = []
    for i in range(8):
        add = 56 + i
        check_pcf = PCF8574(1, add)

        try:
            print(check_pcf.port)
            addresses.append(hex(add))
        except (IOError, TypeError):
            pass
    print("Adrresses responding {}".format(addresses))
    if len(addresses) > 2:
        print("PCF responds on all addresses")
        exit()


def compare(list1, list2):
    if len(list1) != len(list2):
        return False
    for i in range(len(list1)):
        if list1[i] != list2[i]:
            return False
    return True


def read(pcf):
    try:
        ret = pcf.port
        print(ret)
    except (IOError, TypeError):
        return [False]


def main():
    scan()

    for i in range(8):
        tester_pcf.port[i] = False

    sleep(0.005)
    res = [False]*8
    if not compare(tester_pcf.port, res):
        print("Tester failed to setup with all false")
        exit()

    if not dut.port == res:
        print("DUT failed read values")
        exit()


main()





