import copy
import os
import re
import shutil
import subprocess

from pyhenkan.plugin import LWLibavSource
from pyhenkan.queue import Queue
from pyhenkan.track import AudioTrack, MenuTrack, TextTrack, VideoTrack

from pymediainfo import MediaInfo
from gi.repository import GLib


class MediaFile:
    def __init__(self, path):
        self.path = path
        self.dname, self.bname = os.path.split(self.path)
        self.name, self.ext = os.path.splitext(self.bname)
        self.tmpd = '/'.join([self.dname, self.name + '.tmp'])
        self.oname = ''

        # Set these globally until I want to support multiple video tracks
        self.width = 0
        self.height = 0
        self.fpsnum = 0
        self.fpsden = 1
        self.first = 0
        self.last = 0
        self.filters = [LWLibavSource(self.path)]

        self.mediainfo = MediaInfo.parse(self.path)
        self.uid = self._get_uid()
        self.tracklist = self._get_tracklist()

    def copy(self):
        f = MediaFile(self.path)
        f.width = copy.copy(self.width)
        f.height = copy.copy(self.height)
        f.fpsnum = copy.copy(self.fpsnum)
        f.fpsden = copy.copy(self.fpsden)
        f.first = copy.copy(self.first)
        f.last = copy.copy(self.last)
        f.filters = [copy.deepcopy(f) for f in self.filters]
        for i in range(len(self.tracklist)):
            tc = self.tracklist[i]
            t = f.tracklist[i]
            t.enable = copy.copy(tc.enable)
            t.title = copy.copy(tc.title)
            t.lang = copy.copy(tc.lang)
            t.default = copy.copy(tc.default)
            if t.type in ['Video', 'Audio']:
                t.codec = copy.deepcopy(tc.codec)
        f.oname = copy.copy(self.oname)
        return f

    def compare(self, mediafile):
        if len(self.tracklist) != len(mediafile.tracklist):
            m = ('{} ({} tracks) and {} ({} tracks) differ from each '
                 'other. Please make sure all files share the same '
                 'layout.'
                 ).format(self.bname, str(len(self.tracklist)),
                          mediafile.bname, str(len(mediafile.tracklist)))
        else:
            m = ''

        return m

    def process(self):
        queue = Queue()

        job = queue.tstore.append(None, [None, self.bname, self.oname, '',
                                         'Waiting'])

        for t in self.tracklist:
            if t.type not in ['Text', 'Menu'] and t.enable and t.codec:
                future = queue.executor.submit(t.transcode)
                queue.tstore.append(job, [future, '', '', t.codec.library,
                                          'Waiting'])

        future = queue.executor.submit(self.mux)
        queue.tstore.append(job, [future, '', '', 'mux', 'Waiting'])

    def mux(self):
        queue = Queue()

        print('Mux...')
        o = '/'.join([self.dname, self.oname])

        cmd = ['mkvmerge -o "{}" -D -A -S -B -T "{}"'.format(o, self.path)]

        for t in self.tracklist:
            f = ''
            if t.type == 'Video' and t.enable:
                f = '-A -S -B -T -M -d {} --no-global-tags --no-chapters '
                f += '--track-name {}:"{}" --language {}:"{}" "{}"'
            elif t.type == 'Audio' and t.enable:
                f = '-D -S -B -T -M -a {} --no-global-tags --no-chapters '
                f += '--track-name {}:"{}" --language {}:"{}" "{}"'
            elif t.type == 'Text' and t.enable:
                f = '-D -A -B -T -M -s {} --no-global-tags --no-chapters '
                f += '--track-name {}:"{}" --language {}:"{}" "{}"'
            elif t.type == 'Menu' and t.enable:
                f = '-D -A -S -T -M -b {} --no-global-tags --no-chapters '
                f += '--track-name {}:"{}" --language {}:"{}" "{}"'
            if f:
                f = f.format(t.id, t.id, t.title, t.id,
                             t.lang if t.lang else 'und',
                             t.tmpfilepath if t.tmpfilepath else self.path)
                cmd.append(f)

        if self.uid:
            u = '--segment-uid ' + self.uid
            cmd.append(u)

        cmd = ' '.join(cmd)
        print(cmd)

        self.proc = subprocess.Popen(cmd, shell=True,
                                     stdout=subprocess.PIPE,
                                     universal_newlines=True)

        GLib.idle_add(queue.pbar.set_fraction, 0)
        GLib.idle_add(queue.pbar.set_text, 'Muxing...')
        while self.proc.poll() is None:
            line = self.proc.stdout.readline()
            if 'Progress:' in line:
                f = int(re.findall('[0-9]+', line)[0]) / 100
                GLib.idle_add(queue.pbar.set_fraction, f)
        if self.proc.poll() < 0:
            GLib.idle_add(queue.pbar.set_text, 'Failed')
        else:
            GLib.idle_add(queue.pbar.set_text, 'Ready')
        GLib.idle_add(queue.pbar.set_fraction, 0)

    def clean(self):
        queue = Queue()

        print('Delete temporary files...')
        shutil.rmtree(self.tmpd)

        GLib.add(queue.pbar.set_fraction, 0)
        GLib.add(queue.pbar.set_text, 'Ready')

    def _get_uid(self):
        if self.mediainfo.tracks[0].other_unique_id is not None:
            uid = self.mediainfo.tracks[0].other_unique_id[0]
            uid = re.findall('0x[^)]*', uid)[0].replace('0x', '')
            # Mediainfo strips leading zeroes
            uid = uid.rjust(32, '0')

        return uid if self.ext == '.mkv' else ''

    def _get_tracklist(self):
        tracklist = []
        # Track: [track_id, track_type]
        for t in self.mediainfo.tracks:
            if t.track_type == 'Video':
                tr = VideoTrack()
                # tr.width = t.width
                # tr.height = t.height
                # tr.fpsnum, tr.fpsden = self._get_fps(t.frame_rate_mode,
                #                                      t.frame_rate)
                self.width = t.width
                self.height = t.height
                self.fpsnum, self.fpsden = self._get_fps(t.frame_rate_mode,
                                                         t.frame_rate)
            elif t.track_type == 'Audio':
                tr = AudioTrack()
                tr.channel = t.channel_s
                tr.rate = t.sampling_rate
                tr.depth = t.bit_depth

            elif t.track_type == 'Text':
                tr = TextTrack()

            elif t.track_type == 'Menu':
                tr = MenuTrack()

            if t.track_type != 'General':
                tr.file = self
                tr.id = (t.track_id if t.track_id else 0) - 1
                tr.type = t.track_type
                tr.format = t.format
                if t.title:
                    tr.title = t.title
                # We want the 3 letter code
                if t.other_language:
                    tr.lang = t.other_language[3]

                tracklist.append(tr)

        return tracklist

    def _get_fps(self, fps_mode, fps):
        if fps_mode == 'CFR':
            if fps == '23.976':
                fpsnum = 24000
                fpsden = 1001
            elif fps_mode == '29.970':
                fpsnum = 30000
                fpsden = 1001
            return fpsnum, fpsden
        return 0, 1

# vim: ts=4 sw=4 et:
