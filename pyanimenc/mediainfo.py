import re

import pyanimenc.conf as conf
from pyanimenc.tracks import VideoTrack, AudioTrack, TextTrack, MenuTrack
from pymediainfo import MediaInfo


class Parse:
    def __init__(self, f):
        self.m = MediaInfo.parse(f)

    def get_uid(self):
        uid = self.m.tracks[0].other_unique_id[0]
        uid = re.findall('0x[^)]*', uid)[0].replace('0x', '')
        # Mediainfo strips leading zeroes...
        uid = uid.rjust(32, '0')

    def get_tracklist(self):
        tracklist = []
        # Track: [track_id, track_type]
        for t in self.m.tracks:
            if t.track_type == 'Video':
                track = VideoTrack()
                track.height = t.height
                track.width = t.width
                track.fpsnum, track.fpsden = self._get_fps(t.frame_rate_mode,
                                                           t.frame_rate)
            elif t.track_type == 'Audio':
                track = AudioTrack()
                track.channels = t.channel_s
                track.rate = t.sampling_rate
                track.depth = t.bit_depth

            elif t.track_type == 'Text':
                track = TextTrack()
                track.encode = False

            elif t.track_type == 'Menu':
                track = MenuTrack()
                track.encode = False

            if t.track_type != 'General':
                track.id = t.track_id - 1
                track.type = t.track_type
                track.format = t.format
                if t.title:
                    track.title = t.title
                # We want the 3 letter code
                if t.other_language:
                    track.lang = t.other_language[3]

                tracklist.append(track)

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
