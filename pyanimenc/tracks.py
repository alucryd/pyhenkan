class Track:
    def __init__(self):
        self.id = 0
        self.enable = True
        self.encode = True
        self.type = ''
        self.format = ''
        self.title = ''
        self.lang = 'und'
        self.default = True


class VideoTrack(Track):
    def __init__(self):
        super().__init__()
        self.width = 0
        self.height = 0
        self.fpsnum = 0
        self.fpsden = 1


class AudioTrack(Track):
    def __init__(self):
        super().__init__()
        self.channels = 0
        self.rate = 0
        self.depth = 0


class TextTrack(Track):
    def __init__(self):
        super().__init__()


class MenuTrack(Track):
    def __init__(self):
        super().__init__()
