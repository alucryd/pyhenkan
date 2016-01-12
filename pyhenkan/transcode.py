import re
import subprocess

from pyhenkan.queue import Queue
from pyhenkan.vapoursynth import VapourSynth

from gi.repository import GLib


class Transcode:
    def __init__(self, track, pbar):
        self.track = track
        self.pbar = pbar
        self.queue = Queue()

    def script(self, vpy, filters):
        print('Create VapourSynth script...')
        s = VapourSynth(self.track.file).get_script()

        self.vpy = vpy

        print('Write ' + self.vpy)
        with open(self.vpy, 'w') as f:
            f.write(s)

    def info(self):
        cmd = 'vspipe "{}" - -i'.format(self.vpy)
        proc = subprocess.Popen(cmd, shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL,
                                universal_newlines=True)
        while proc.poll() is None:
            line = proc.stdout.readline()
            # Get the frame total
            if 'Frames:' in line:
                dur = int(line.split(' ')[1])
        return dur

    def preview(self):
        cmd = 'vspipe "{}" /dev/null'.format(self.vpy)
        print(cmd)
        subprocess.run(cmd, shell=True,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       universal_newlines=True)

    def video(self):
        print('Encode video...')
        o = '/'.join([self.track.file.tmpd, self.track.file.name])

        cmd = self.track.codec.command(self.vpy, o)
        print(cmd)

        self.queue.proc = subprocess.Popen(cmd, shell=True,
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.PIPE,
                                           universal_newlines=True)

        # Progress
        GLib.idle_add(self.pbar.set_fraction, 0)
        GLib.idle_add(self.pbar.set_text, 'Encoding video...')

        self.queue.update()

        proc = self.queue.proc
        d = self.info()
        while proc.poll() is None:
            line = proc.stderr.readline()
            # Get the current frame
            if re.match('^[0-9]+ ', line):
                p = int(line.split(' ')[0])
                f = round(p / d, 2)
                GLib.idle_add(self.pbar.set_fraction, f)
        if proc.poll() < 0:
            GLib.idle_add(self.pbar.set_text, 'Failed')
        else:
            GLib.idle_add(self.pbar.set_text, 'Ready')
        GLib.idle_add(self.pbar.set_fraction, 0)

        # Update path and id
        self.track.tmpfilepath = '.'.join([o, self.track.codec.container])
        self.track.id = 0

    def audio(self):
        print('Encode audio...')
        o = '_'.join([self.track.file.name, str(self.track.id)])
        o = '/'.join([self.track.file.tmpd, o])

        cmd = self.track.codec.command(self.track, o)
        print(cmd)

        self.queue.proc = subprocess.Popen(cmd, shell=True,
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.PIPE,
                                           universal_newlines=True)

        # Progress
        GLib.idle_add(self.pbar.set_fraction, 0)
        GLib.idle_add(self.pbar.set_text, 'Encoding audio...')

        self.queue.update()

        proc = self.queue.proc
        while proc.poll() is None:
            line = proc.stderr.readline()
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
                GLib.idle_add(self.pbar.set_fraction, f)
        if proc.poll() < 0:
            GLib.idle_add(self.pbar.set_text, 'Failed')
        else:
            GLib.idle_add(self.pbar.set_text, 'Ready')
        GLib.idle_add(self.pbar.set_fraction, 0)

        # Update path and id
        self.track.tmpfilepath = '.'.join([o, self.track.codec.container])
        self.track.id = 0

# vim: ts=4 sw=4 et:
