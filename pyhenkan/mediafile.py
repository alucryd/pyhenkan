import os
import re
import shutil

import pyhenkan.conf as conf
from pyhenkan.queue import Queue
from pyhenkan.mux import Mux
from pyhenkan.track import VideoTrack, AudioTrack, TextTrack, MenuTrack

from pymediainfo import MediaInfo
from gi.repository import GLib


class MediaFile:
    def __init__(self, f):
        self.path = f
        self.dname, self.bname = os.path.split(self.path)
        self.name, self.ext = os.path.splitext(self.bname)
        self.tmpd = '/'.join([self.dname, self.name + '.tmp'])

        self.mediainfo = MediaInfo.parse(f)
        self.uid = self._get_uid()
        self.tracklist = self._get_tracklist()

        self.oname = self.name
        self.osuffix = 'new'
        self.ocont = ''

        self.queue = Queue()

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

    def process(self, pbar):
        job = self.queue.tstore.append(None, [None, self.bname, '', 'Waiting'])

        self.queue.worker.submit(self._create_tmpdir)

        for t in self.tracklist:
            if t.enable and t.encode:
                t.process(job, pbar)

        future = self.queue.worker.submit(Mux(self, pbar).mux)
        self.queue.tstore.append(job, [future, '', 'mux', 'Waiting'])

    def clean(self, pbar):
        print('Delete temporary files...')
        shutil.rmtree(self.tmpd)

        GLib.add(pbar.set_fraction, 0)
        GLib.add(pbar.set_text, 'Ready')

    def _create_tmpdir(self):
        if not os.path.isdir(self.tmpd):
            os.mkdir(self.tmpd)

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
                tr.height = t.height
                tr.width = t.width
                tr.fpsnum, tr.fpsden = self._get_fps(t.frame_rate_mode,
                                                     t.frame_rate)
            elif t.track_type == 'Audio':
                tr = AudioTrack()
                tr.channels = t.channel_s
                tr.rate = t.sampling_rate
                tr.depth = t.bit_depth

            elif t.track_type == 'Text':
                tr = TextTrack()
                tr.encode = False

            elif t.track_type == 'Menu':
                tr = MenuTrack()
                tr.encode = False

            if t.track_type != 'General':
                tr.file = self
                tr.id = t.track_id - 1
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

            conf.video['fpsnum'] = fpsnum
            conf.video['fpsden'] = fpsden

            return fpsnum, fpsden

# vim: ts=4 sw=4 et:
