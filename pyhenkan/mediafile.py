import copy
import os
import re
import shutil
import subprocess

from pyhenkan.environment import Environment
from pyhenkan.plugin import LWLibavSource, LibavSMASHSource, FFmpegSource
from pyhenkan.queue import Queue
from pyhenkan.track import AudioTrack, TextTrack, VideoTrack

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
        # Store current and original values
        self.dimensions = [0, 0, 0, 0]
        self.fps = [0, 1, 0, 1]
        self.trim = [0, 0]

        env = Environment()
        if env.source_plugins['LWLibavSource'][1]:
            self.filters = [LWLibavSource()]
        elif env.source_plugins['LibavSMASHSource'][1]:
            self.filters = [LibavSMASHSource()]
        elif env.source_plugins['FFmpegSource'][1]:
            self.filters = [FFmpegSource()]

        self.parse()

    def copy(self):
        f = MediaFile(self.path)
        f.dimensions = copy.copy(self.dimensions)
        f.fps = copy.copy(self.fps)
        f.trim = copy.copy(self.trim)
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

        cmd = 'mkvmerge -o "{}" -D -A -S -B -T "{}"'.format(o, self.path)

        for t in self.tracklist:
            f = ''
            if t.type == 'Video' and t.enable:
                f += ' -A -S -B -T -M -d'
            elif t.type == 'Audio' and t.enable:
                f += ' -D -S -B -T -M -a'
            elif t.type == 'Text' and t.enable:
                f += ' -D -A -B -T -M -s'
            elif t.type == 'Menu' and t.enable:
                f += ' -D -A -S -T -M -b'
            if f:
                f += ' {id} --no-global-tags --no-chapters'
                f += ' --track-name {id}:"{title}" --language {id}:"{lang}"'
                if t.default:
                    f += ' --default-track {id}'
                f += ' "{path}"'
                lang = t.lang if t.lang else 'und'
                path = t.tmpfilepath if t.tmpfilepath else self.path
                f = f.format(id=t.id,  title=t.title, lang=lang, path=path)
                cmd += f

        if self.uid:
            u = ' --segment-uid ' + self.uid
            cmd += u

        print(cmd)

        self.proc = subprocess.Popen(cmd, shell=True,
                                     stdout=subprocess.PIPE,
                                     universal_newlines=True)

        GLib.idle_add(queue.pbar.set_fraction, 0)
        GLib.idle_add(queue.pbar.set_text, 'Muxing...')

        queue.update()

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

    def parse(self):
        self.tracklist = []
        mediainfo = MediaInfo.parse(self.path)

        # UID
        if self.ext == '.mkv' and mediainfo.tracks[0].other_unique_id:
            uid = mediainfo.tracks[0].other_unique_id[0]
            uid = re.findall('0x[^)]*', uid)[0].replace('0x', '')
            # Mediainfo strips leading zeroes
            self.uid = uid.rjust(32, '0')

        # Track: [track_id, track_type]
        for t in mediainfo.tracks:
            if t.track_type == 'Video':
                tr = VideoTrack()
                self.dimensions[0] = t.width
                self.dimensions[2] = t.width
                self.dimensions[1] = t.height
                self.dimensions[3] = t.height
                if t.frame_rate_mode == 'CFR':
                    if t.frame_rate == '23.976':
                        self.fps[0] = 24000
                        self.fps[2] = 24000
                        self.fps[1] = 1001
                        self.fps[3] = 1001
                    elif t.frame_rate == '29.970':
                        self.fps[0] = 30000
                        self.fps[2] = 30000
                        self.fps[1] = 1001
                        self.fps[3] = 1001
            elif t.track_type == 'Audio':
                tr = AudioTrack()
                tr.channel = t.channel_s
                tr.rate = t.sampling_rate
                tr.depth = t.bit_depth

            elif t.track_type == 'Text':
                tr = TextTrack()

            elif t.track_type == 'Menu':
                # tr = MenuTrack()
                pass

            if t.track_type not in ['General', 'Menu']:
                tr.file = self
                tr.id = t.track_id - 1
                tr.default = True if t.default == 'Yes' else False
                tr.type = t.track_type
                tr.format = t.format
                tr.title = t.title if t.title else ''
                # We want the 3 letter code
                tr.lang = t.other_language[3] if t.other_language else ''

                self.tracklist.append(tr)

# vim: ts=4 sw=4 et:
