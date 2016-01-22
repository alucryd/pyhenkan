import re
import subprocess

from pyhenkan.queue import Queue
from pyhenkan.vapoursynth import VapourSynth

from gi.repository import GLib


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

    def get_total_frame(self, vpy):
        cmd = 'vspipe "{}" - -i'.format(vpy)
        proc = subprocess.Popen(cmd, shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL,
                                universal_newlines=True)
        while proc.poll() is None:
            line = proc.stdout.readline()
            # Get the number of frames
            if 'Frames:' in line:
                tf = int(line.split(' ')[1])
        return tf

    def transcode(self):
        print('transcode video')
        queue = Queue()

        print('Create VapourSynth script...')
        s = VapourSynth(self.file).get_script()
        vpy = '/'.join([self.file.tmpd, self.file.name + '.vpy'])

        print('Write ' + vpy)
        with open(vpy, 'w') as f:
            f.write(s)

        print('Encode video...')
        o = '/'.join([self.file.tmpd, self.file.name])

        cmd = ' '.join(self.codec.get_cmd(vpy, o))
        print(cmd)

        queue.proc = subprocess.Popen(cmd, shell=True,
                                      stdout=subprocess.DEVNULL,
                                      stderr=subprocess.PIPE,
                                      universal_newlines=True)

        # Progress
        GLib.idle_add(queue.pbar.set_fraction, 0)
        GLib.idle_add(queue.pbar.set_text, 'Encoding video...')

        queue.update()

        # Get the number of frames
        d = self.get_total_frame(vpy)

        while queue.proc.poll() is None:
            line = queue.proc.stderr.readline()
            # Get the current frame
            if 'frame=' in line:
                p = int(re.findall('[0-9]+', line)[0])
                f = round(p / d, 2)
                GLib.idle_add(queue.pbar.set_fraction, f)
        if queue.proc.poll() < 0:
            GLib.idle_add(queue.pbar.set_text, 'Failed')
        else:
            GLib.idle_add(queue.pbar.set_text, 'Ready')
        GLib.idle_add(queue.pbar.set_fraction, 0)

        # Update path and id
        self.tmpfilepath = '.'.join([o, self.codec.container])
        self.id = 0


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

    def transcode(self):
        print('transcode audio')
        queue = Queue()

        print('Encode audio...')
        o = '_'.join([self.file.name, str(self.id)])
        o = '/'.join([self.file.tmpd, o])

        cmd = ' '.join(self.codec.get_cmd(self, o))
        print(cmd)

        queue.proc = subprocess.Popen(cmd, shell=True,
                                      stdout=subprocess.DEVNULL,
                                      stderr=subprocess.PIPE,
                                      universal_newlines=True)

        # Progress
        GLib.idle_add(queue.pbar.set_fraction, 0)
        GLib.idle_add(queue.pbar.set_text, 'Encoding audio...')

        queue.update()

        while queue.proc.poll() is None:
            line = queue.proc.stderr.readline()
            # Get the clip duration
            if 'Duration:' in line:
                d = re.findall('[0-9]{2}:[0-9]{2}:[0-9]{2}', line)[0]
                h, m, s = d.split(':')
                d = int(h) * 3600 + int(m) * 60 + int(s)
            # Get the current timestamp
            if 'time=' in line:
                p = re.findall('[0-9]{2}:[0-9]{2}:[0-9]{2}', line)[0]
                h, m, s = p.split(':')
                p = int(h) * 3600 + int(m) * 60 + int(s)
                f = round(p / d, 2)
                GLib.idle_add(queue.pbar.set_fraction, f)
        if queue.proc.poll() < 0:
            GLib.idle_add(queue.pbar.set_text, 'Failed')
        else:
            GLib.idle_add(queue.pbar.set_text, 'Ready')
        GLib.idle_add(queue.pbar.set_fraction, 0)

        # Update path and id
        self.tmpfilepath = '.'.join([o, self.codec.container])
        self.id = 0


class TextTrack(Track):
    def __init__(self):
        super().__init__()


class MenuTrack(Track):
    def __init__(self):
        super().__init__()

# vim: ts=4 sw=4 et:
