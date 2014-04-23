#!/usr/bin/env python3

import os
import re
import subprocess
from random import randrange
from decimal import Decimal
from lxml import etree

class MatroskaOps:
    def __init__(self, source):
        self.source = source
        self.sname = os.path.splitext(self.source)[0]

    def _get_text(self, line):
        text = line.split(':', 1)[1]
        return text.strip()

    def get_data(self):
        data = {}
        mkvinfo = subprocess.Popen('mkvinfo "' + self.source + '"', shell=True,
                                   stdout=subprocess.PIPE)
        line = mkvinfo.stdout.readline().decode()
        while line:
            if 'Segment UID:' in line:
                uid = self._get_text(line)
                uid = re.sub(' ?0x', '', uid)
                data['uid'] = uid
            if 'Track number:' in line:
                track = {}
                num = self._get_text(line)
                num = num.split(':')[1]
                num = (num.strip()).strip(')')
            if 'Codec ID:' in line:
                codec = self._get_text(line)
                track['codec'] = codec
                data['track' + num] = track
            if 'Language:' in line:
                lang = self._get_text(line)
                track['lang'] = lang
                data['track' + num] = track
            if 'Channels:' in line:
                channels = self._get_text(line)
                track['channels'] = channels
                data['track' + num] = track
            line = mkvinfo.stdout.readline().decode()
        return data

    def extract(self, tracks):
        track = tracks[0]
        x = 'mkvextract tracks "{}"'.format(self.source)
        t = '{}:"{}"'.format(track[0], track[2])
        cmd = [x, t]
        if len(tracks) >= 2:
            for track in tracks[1:]:
                t = '{}:"{}"'.format(track[0], track[2])
                cmd.append(t)
        subprocess.call(' '.join(cmd), shell=True)

    def merge(self, vid_track, aud_tracks, sub_tracks=[], uid=''):
        if not os.path.isdir('out'):
            os.mkdir(os.getcwd() + '/out')
        x = ('mkvmerge -o "out/{}.mkv" '
             '-D -A -S "{}"').format(self.sname, self.source)
        v = ('-A -S -M --no-chapters --language '
             '{}:{} "{}"').format(vid_track[0], vid_track[1], vid_track[2])
        cmd = [x, v]
        for aud_track in aud_tracks:
            a = ('--no-chapters --language '
                 '0:{} "{}"').format(aud_track[1], aud_track[2])
            cmd.append(a)
        if sub_tracks:
            for sub_track in sub_tracks:
                s = '--language 0:{} "{}"'.format(sub_track[1], sub_track[2])
                cmd.append(s)
        if uid:
            u = '--segment-uid ' + uid
            cmd.append(u)
        subprocess.call(' '.join(cmd), shell=True)

class Chapters:
    def __init__(self, lang='eng', fpsnum=24000, fpsden=1001, ordered=True):
        self.ordered = ordered
        self.lang = lang
        self.fpsnum = fpsnum
        self.fpsden = fpsden

    def timecode(self, frames):
        time = Decimal(frames) * Decimal(self.fpsden) / Decimal(self.fpsnum)
        hours = int(time // 3600)
        minutes = int((time - hours * 3600) // 60)
        seconds = round(time - hours * 3600 - minutes * 60, 3)
        return '{:0>2d}:{:0>2d}:{:0>12.9f}'.format(hours, minutes, seconds)

    def _atom(self, chapter):
        atom = etree.Element('ChapterAtom')
        uid = etree.SubElement(atom, 'ChapterUID')
        uid.text = str(randrange(1000000000))
        if self.ordered:
            seg_uid = etree.SubElement(atom, 'ChapterSegmentUID', format='hex')
            seg_uid.text = chapter[3]
        display = etree.SubElement(atom, 'ChapterDisplay')
        string = etree.SubElement(display, 'ChapterString')
        string.text = chapter[0]
        lang = etree.SubElement(display, 'ChapterLanguage')
        lang.text = self.lang
        start = etree.SubElement(atom, 'ChapterTimeStart')
        start.text = self.timecode(chapter[1])
        if self.ordered:
            end = etree.SubElement(atom, 'ChapterTimeEnd')
            end.text = self.timecode(chapter[2])
        return atom

    def chapter(self, chapters):
        chaps = etree.Element('Chapters')
        edit = etree.SubElement(chaps, 'EditionEntry')
        edit_uid = etree.SubElement(edit, 'EditionUID')
        edit_uid.text = str(randrange(1000000000))
        if self.ordered:
            ordered = etree.SubElement(edit, 'EditionFlagOrdered')
            ordered.text = '1'
        for chapter in chapters:
            c = self._atom(chapter)
            edit.append(c)
        doctype = '<!-- <!DOCTYPE Chapters SYSTEM "matroskachapters.dtd"> -->'
        xml = etree.tostring(chaps, encoding='UTF-8', pretty_print=True,
                             xml_declaration=True, doctype=doctype)
        return xml

class Encode:
    def __init__(self, source):
        self.source = source
        self.sname = os.path.splitext(self.source)[0]

    def vpy(self, fpsnum=24000, fpsden=1001, trim=[], crop=[], resize=[],
            deband='', bit_depth=10):
        import vapoursynth as vs
        core = vs.get_core()
        clip = core.ffms2.Source(source=self.source, fpsnum=fpsnum,
                                 fpsden=fpsden)
        if trim:
            part = trim[0]
            clip = core.std.Trim(clip=clip, first=part[0], last=part[1])
            if len(trim) >= 2:
                for part in trim[1:]:
                    clip = clip + core.std.Trim(clip=clip, first=part[0],
                                                last=part[1])
        if len(crop) == 4:
            clip = core.std.CropRel(clip=clip, left=crop[0], right=crop[1],
                                    top=crop[2], bottom=crop[3])
        if deband:
            clip = core.f3kdb.Deband(clip=clip, preset=deband,
                                     output_depth=bit_depth)
        if len(resize) == 2:
            clip = core.resize.Bicubic(clip=clip, width=resize[0],
                                       height=resize[1])
        clip.set_output()

    def video(self, q=15, d=10, p='slow', t='animation', preview=False):
        dec = 'vspipe "{}.vpy" - -y4m'.format(self.sname)
        if preview:
            enc = 'mpv -'
        else:
            if d == 10:
                x = 'x264-10bit'
            elif d == 8:
                x = 'x264'
            enc = ('{} - --crf {} --preset {} --tune {} --demuxer y4m '
                   '--output "{}.mp4"').format(x, q, p, t, self.sname)
        cmd = (dec, enc)
        subprocess.call(' | '.join(cmd), shell=True)

    def audio(self, q=4, c='m4a'):
        dec = 'ffmpeg -i "{}" -f caf -'.format(self.source)
        enc = 'fdkaac - -m{} -o "{}.{}"'.format(q, self.sname, c)
        cmd = (dec, enc)
        subprocess.call(' | '.join(cmd), shell=True)

# vim: ts=4 sw=4 et:
