from pyhenkan.queue import Queue
from pyhenkan.transcode import Transcode


class Track:
    def __init__(self):
        self.file = None
        self.tmpfilepath = ''
        self.id = 0
        self.enable = True
        self.type = ''
        self.format = ''
        self.title = ''
        self.lang = ''
        self.default = True

        self.queue = Queue()

    def compare(self, track):
        m = ('{} (track {}: {}) and {} (track {}: {}) have different {}.\n'
             'Please make sure all files share the same layout.')

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
        self.codec = None
        self.width = 0
        self.height = 0
        self.fpsnum = 0
        self.fpsden = 1

    def process(self, job, pbar):
        trans = Transcode(self, pbar)

        vpy = '/'.join([self.file.tmpd, self.file.name + '.vpy'])

        # trans.script(vpy, self.file)
        future = self.queue.worker.submit(trans.script, vpy, self.file.filters)
        self.queue.tstore.append(job, [future, '', 'vpy', 'Waiting'])

        # trans.video()
        future = self.queue.worker.submit(trans.video)
        self.queue.tstore.append(job, [future, '', self.codec.binary,
                                       'Waiting'])


class AudioTrack(Track):
    def __init__(self):
        super().__init__()
        self.codec = None
        self.channel = 0
        self.rate = 0
        self.depth = 0

    def compare(self, track):
        m = super().compare(track)

        if m:
            return m
        else:
            m = ('{} (track {}: {}) and {} (track {}: {}) have different {}.\n'
                 'Please make sure all files share the same layout.')

        if self.channel != track.channel:
            m.format(self.file.bname, str(self.id), self.channel)
            m.format(track.file.bname, str(track.id), track.channel)
            m.format('channels')
        else:
            m = ''

        return m

    def process(self, job, pbar):
        trans = Transcode(self, pbar)

        # trans.audio()
        future = self.queue.worker.submit(trans.audio)
        self.queue.tstore.append(job, [future, '', self.codec.library,
                                       'Waiting'])


class TextTrack(Track):
    def __init__(self):
        super().__init__()


class MenuTrack(Track):
    def __init__(self):
        super().__init__()

# vim: ts=4 sw=4 et:
