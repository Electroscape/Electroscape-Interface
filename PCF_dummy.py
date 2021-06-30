class PCF8574:
    def __init__(self, *discarded):
        print("Using Dummy PCF class")
        self.port = [False] * 8
