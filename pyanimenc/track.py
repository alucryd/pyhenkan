from pyanimenc.queue import Queue
from pyanimenc.transcode import Transcode


class Track:
    def __init__(self):
        self.file = None
        self.id = 0
        self.enable = True
        self.encode = True
        self.type = ''
        self.format = ''
        self.title = ''
        self.lang = 'und'
        self.default = True

        self.tmpfilepath = ''
        self.queue = Queue()

    def compare(self, track):
        m = ('{} (track {}: {}) and {} (track {}: {}) have different {}.\n'
             'Please make sure all files share the same layout.')

        print(self.type)
        print(track.type)
        if self.type != track.type:
            m = m.format(self.file.bname, str(self.id), self.type,
                         track.file.bname, str(track.id), track.type,
                         'types')
        elif self.format != track.format:
            m = m.format(self.file.bname, str(self.id), self.format,
                         track.file.bname, str(track.id), track.format,
                         'formats')
        elif self.lang != track.lang:
            m = m.format(self.file.bname, str(self.id), self.lang,
                         track.file.bname, str(track.id), track.lang,
                         'languages')
        else:
            m = ''

        return m


class VideoTrack(Track):
    def __init__(self):
        super().__init__()
        self.codec = []
        self.width = 0
        self.height = 0
        self.fpsnum = 0
        self.fpsden = 1
        self.filters = []

    def process(self, job, pbar):
        trans = Transcode(self, pbar)

        vpy = '/'.join([self.file.tmpd, self.file.name + '.vpy'])

        future = self.queue.worker.submit(trans.script, vpy, self.filters)
        self.queue.tstore.append(job, [future, '', 'vpy', 'Waiting'])

        future = self.queue.worker.submit(trans.video, self.codec)
        self.queue.tstore.append(job, [future, '', self.codec[0], 'Waiting'])


class AudioTrack(Track):
    def __init__(self):
        super().__init__()
        self.codec = []
        self.channels = 0
        self.rate = 0
        self.depth = 0
        self.filters = []

    def compare(self, track):
        m = super().compare(track)

        if m:
            return m
        else:
            m = ('{} (track {}: {}) and {} (track {}: {}) have different {}.\n'
                 'Please make sure all files share the same layout.')

        if self.channels != track.channels:
            m.format(self.file.bname, str(self.id), self.channels)
            m.format(track.file.bname, str(track.id), track.channels)
            m.format('channels')
        else:
            m = ''

        return m

    def process(self, job, pbar):
        trans = Transcode(self, pbar)

        future = self.queue.worker.submit(trans.audio, self.codec,
                                          self.filters)
        self.queue.tstore.append(job, [future, '', self.codec[0], 'Waiting'])


class TextTrack(Track):
    def __init__(self):
        super().__init__()


class MenuTrack(Track):
    def __init__(self):
        super().__init__()

# vim: ts=4 sw=4 et:
