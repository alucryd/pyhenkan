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
            if '+ Segment UID:' in line:
                uid = self._get_text(line)
                uid = re.sub(' ?0x', '', uid)
                data['uid'] = uid
            if '+ Track number:' in line:
                track = {}
                num = self._get_text(line)
                num = num.split(':')[1]
                num = (num.strip()).strip(')')
            if '+ Codec ID:' in line:
                codec = self._get_text(line)
                track['codec'] = codec
                data['track' + num] = track
            if '+ Name:' in line:
                name = self._get_text(line)
                track['name'] = name
                data['track' + num] = track
            if '+ Language:' in line:
                lang = self._get_text(line)
                track['lang'] = lang
                data['track' + num] = track
            if '+ Channels:' in line:
                channels = self._get_text(line)
                track['channels'] = channels
                data['track' + num] = track
            line = mkvinfo.stdout.readline().decode()
        return data

    def extract(self, tracks):
        # [[id, filename, extension]...]
        track = tracks[0]
        x = 'mkvextract tracks "{}"'.format(self.source)
        t = '{}:"{}.{}"'.format(track[0], track[1], track[2])
        cmd = [x, t]
        if len(tracks) > 1:
            for track in tracks[1:]:
                t = '{}:"{}.{}"'.format(track[0], track[1],
                                           track[2])
                cmd.append(t)
        cmd = ' '.join(cmd)
        return cmd

    def merge(self, output, vtrack, atracks=[], stracks=[], uid=''):
        # [[id, filename, extension, name, language]...]
        x = 'mkvmerge -o "{}" -D -A -S -T "{}"'.format(output, self.source)
        v = ('-A -S -M -T -d {} --no-global-tags --no-chapters '
             '--track-name {}:"{}" --language {}:"{}" "{}"'
            ).format(vtrack[0], vtrack[0], vtrack[3], vtrack[0], vtrack[4],
                     vtrack[1] + '.' + vtrack[2])
        cmd = [x, v]
        if atracks:
            for track in atracks:
                a = ('-D -S -M -T -a {} --no-global-tags --no-chapters '
                     '--track-name {}:"{}" --language {}:"{}" "{}"'
                    ).format(track[0], track[0], track[3], track[0], track[4],
                             track[1] + '.' + track[2])
                cmd.append(a)
        if stracks:
            for track in stracks:
                s = ('-D -A -M -T -s {} --no-global-tags --no-chapters '
                     '--track-name {}:"{}" --language {}:"{}" "{}"'
                    ).format(track[0], track[0], track[3], track[0], track[4],
                             track[1] + '.' + track[2])
                cmd.append(s)
        if uid:
            u = '--segment-uid ' + uid
            cmd.append(u)
        cmd = ' '.join(cmd)
        return cmd

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

    def info(self):
        cmd = 'vspipe "{}.vpy" - -info'.format(self.sname)
        return cmd

    def preview(self):
        dec = 'vspipe "{}.vpy" - -y4m'.format(self.sname)
        enc = 'mpv -'
        cmd = ' | '.join([dec, enc])
        return cmd

    def x264(self, o='', d=8, q=18, p='medium', t='', c='mp4'):
        if not o:
            o = self.sname
        dec = 'vspipe "{}.vpy" - -y4m'.format(self.sname)
        if d == 8:
            x = 'x264'
        elif d == 10:
            x = 'x264-10bit'
        enc = '{} - --crf {} --demuxer y4m --output "{}.{}"'.format(x, q, o, c)
        if p:
            enc = enc + ' --preset ' + p
        if t:
            enc = enc + ' --tune ' + t
        cmd = ' | '.join([dec, enc])
        return cmd

    def x265(self, o='', d=8, q=18, p='medium', t='', c='265'):
        if not o:
            o = self.sname
        dec = 'vspipe "{}.vpy" - -y4m'.format(self.sname)
        if d == 8:
            x = 'x265'
        elif d == 10:
            x = 'x265-10bit'
        enc = '{} - --crf {} --y4m --output "{}.{}"'.format(x, q, o, c)
        if p:
            enc = enc + ' --preset ' + p
        if t:
            enc = enc + ' --tune ' + t
        cmd = ' | '.join([dec, enc])
        return cmd

    def fdkaac(self, o='', m='CBR', b='192', q=4, c='m4a'):
        if not o:
            o = self.sname
        dec = 'ffmpeg -i "{}" -f caf -'.format(self.source)
        if m == 'CBR':
            enc = 'fdkaac - -b {} -o "{}.{}"'.format(b, o, c)
        elif m == 'VBR':
            enc = 'fdkaac - -m {} -o "{}.{}"'.format(q, o, c)
        cmd = ' | '.join([ dec, enc ])
        return cmd

    def lame(self, o='', m='CBR', b=320, q=4):
        if not o:
            o = self.sname
        dec = 'ffmpeg -i "{}" -f wav -'.format(self.source)
        if m == 'CBR':
            enc = 'lame -b {} --cbr - "{}.mp3"'.format(b, o)
        elif m == 'ABR':
            enc = 'lame -b {} --abr - "{}.mp3"'.format(b, o)
        elif m == 'VBR':
            enc = 'lame -V {} - "{}.mp3"'.format(q, o)
        cmd = ' | '.join([ dec, enc ])
        return cmd

# vim: ts=4 sw=4 et:
