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
        v = '-A -S -M -T -d {} --no-global-tags --no-chapters '
        v = v + '--track-name {}:"{}" --language {}:"{}" "{}"'
        v = v.format(vtrack[0], vtrack[0], vtrack[3], vtrack[0], vtrack[4],
                     vtrack[1] + '.' + vtrack[2])
        cmd = [x, v]
        if atracks:
            for track in atracks:
                a = '-D -S -M -T -a {} --no-global-tags --no-chapters '
                a = a + '--track-name {}:"{}" --language {}:"{}" "{}"'
                a = a.format(track[0], track[0], track[3], track[0], track[4],
                             track[1] + '.' + track[2])
                cmd.append(a)
        if stracks:
            for track in stracks:
                s = '-D -A -M -T -s {} --no-global-tags --no-chapters '
                s = s + '--track-name {}:"{}" --language {}:"{}" "{}"'
                s = s.format(track[0], track[0], track[3], track[0], track[4],
                             track[1] + '.' + track[2])
                cmd.append(s)
        if uid:
            u = '--segment-uid ' + uid
            cmd.append(u)
        cmd = ' '.join(cmd)
        return cmd

class Chapters:
    def __init__(self, ordered=False, frame=False, fpsnum=24000, fpsden=1001):
        self.ordered = ordered
        self.frame = frame
        self.fpsnum = fpsnum
        self.fpsden = fpsden

    def frame_to_time(self, frames):
        time = Decimal(frames) * Decimal(self.fpsden) / Decimal(self.fpsnum)
        hours = int(time // 3600)
        minutes = int((time - hours * 3600) // 60)
        seconds = round(time - hours * 3600 - minutes * 60, 3)
        return '{:0>2d}:{:0>2d}:{:0>12.9f}'.format(hours, minutes, seconds)

    def time_to_frame(self, time):
        hours, minutes, seconds = time.split(':')
        s = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        f = round(Decimal(s) * Decimal(self.fpsnum) / Decimal(self.fpsden))

        return f

    def _atom(self, chapter):
        atom = etree.Element('ChapterAtom')
        uid = etree.SubElement(atom, 'ChapterUID')
        uid.text = str(randrange(1000000000))
        if self.ordered:
            seg_uid = etree.SubElement(atom, 'ChapterSegmentUID', format='hex')
            seg_uid.text = chapter[4]
        display = etree.SubElement(atom, 'ChapterDisplay')
        string = etree.SubElement(display, 'ChapterString')
        string.text = chapter[0]
        lang = etree.SubElement(display, 'ChapterLanguage')
        lang.text = chapter[1]
        start = etree.SubElement(atom, 'ChapterTimeStart')
        if self.frame:
            start.text = self.frame_to_time(chapter[2])
        else:
            start.text = chapter[2]
        if self.ordered:
            end = etree.SubElement(atom, 'ChapterTimeEnd')
            if self.frame:
                end.text = self.frame_to_time(chapter[3])
            else:
                end.text = chapter[3]
        return atom

    def build(self, chapters):
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

    def parse(self, xml):
        ordered = False
        chapters = []
        root = etree.fromstring(xml)

        for child in root[0]:
            if child.tag == 'EditionFlagOrdered' and child.text == '1':
                ordered = True
            elif child.tag == 'ChapterAtom':
                title = ''
                lang = 'und'
                start = '00:00:00.000000000'
                end = '00:00:00.000000000'
                uid = ''
                for gchild in child:
                    if gchild.tag == 'ChapterSegmentUID' and gchild.text:
                        uid = gchild.text
                    elif gchild.tag == 'ChapterTimeStart':
                        start = gchild.text
                    elif gchild.tag == 'ChapterTimeEnd':
                        end = gchild.text
                    elif gchild.tag == 'ChapterDisplay':
                        for ggchild in gchild:
                            if ggchild.tag == 'ChapterString':
                                title = ggchild.text
                            elif ggchild.tag == 'ChapterLanguage':
                                lang = ggchild.text

                chapters.append([title, lang, start, end, uid])

        return (ordered, chapters)

class Encode:
    def __init__(self, source):
        self.source = source
        self.sname = os.path.splitext(self.source)[0]

    def vpy(self, filters):
        s = []
        s.append('import vapoursynth as vs')
        s.append('core = vs.get_core()')
        for f in filters:
            line = 'clip = core.'
            args = ['clip']
            if f[0] == 'Source':
                if f[1] == 'FFMpegSource':
                    line = line + 'ffms2.Source'
                elif f[1] in ['LibavSMASHSource', 'LWLibavSource']:
                    line = line + 'lsmas.' + f[1]
                args = ['"{}"'.format(self.source)]
            elif f[0] == 'Crop':
                line = line + 'std.' + f[1]
            elif f[0] == 'Resize':
                line = line + 'resize.' + f[1]
            elif f[0] == 'Denoise':
                if f[1] == 'FluxSmoothT':
                    line = line + 'flux.SmoothT'
                elif f[1] == 'FluxSmoothST':
                    line = line + 'flux.SmoothST'
                elif f[1] == 'RemoveGrain':
                    line = line + 'rgvs.' + f[1]
                elif f[1] == 'TemporalSoften':
                    line = line + 'focus.' + f[1]
            elif f[0] == 'Deband':
                if f[1] == 'f3kdb':
                    line = line + '.'.join([f[1], f[0]])
            line = line + '({})'
            if f[2]:
                args = args + ['='.join([key, str(f[2][key])]) for key in f[2]]
            s.append(line.format(', '.join(args)))
        s.append('clip.set_output()')
        s = '\n'.join(s)
        return s

    def info(self):
        cmd = 'vspipe "{}" - -i'.format(self.source)
        return cmd

    def preview(self):
        dec = 'vspipe "{}" - -y'.format(self.source)
        enc = 'mpv -'
        cmd = ' | '.join([dec, enc])
        return cmd

    def x264(self, o='', d=8, q=18, p='medium', t='', c='mp4', args=''):
        if not o:
            o = self.sname
        dec = 'vspipe "{}" - -y'.format(self.source)
        if d == 8:
            x = 'x264'
        elif d == 10:
            x = 'x264-10bit'
        enc = [x, '-', '--crf', str(q),  '--demuxer', 'y4m', '--output',
               '"' + o + '.' + c + '"']
        if p:
            enc = enc + ['--preset', p]
        if t:
            enc = enc + ['--tune', t]
        if args:
            enc.append(args)
        enc = ' '.join(enc)
        cmd = ' | '.join([dec, enc])
        return cmd

    def x265(self, o='', d=8, q=18, p='medium', t='', c='265', args=''):
        if not o:
            o = self.sname
        dec = 'vspipe "{}" - -y'.format(self.source)
        enc = ['x265', '-', '--output-depth', str(d), '--crf', str(q), '--y4m',
               '--output', '"' + o + '.' + c + '"']
        if p:
            enc = enc + ['--preset', p]
        if t:
            enc = enc + ['--tune', t]
        if args:
            enc.append(args)
        cmd = ' | '.join([dec, enc])
        return cmd

    def fdkaac(self, o='', m='CBR', b='192', q=4, c='m4a'):
        if not o:
            o = self.sname
        dec = 'ffmpeg -i "{}" -f caf -'.format(self.source)
        if m == 'CBR':
            enc = 'fdkaac --silent - -b {} -o "{}.{}"'.format(b, o, c)
        elif m == 'VBR':
            enc = 'fdkaac --silent - -m {} -o "{}.{}"'.format(q, o, c)
        cmd = ' | '.join([ dec, enc ])
        return cmd

    def lame(self, o='', m='CBR', b=320, q=4):
        if not o:
            o = self.sname
        dec = 'ffmpeg -i "{}" -f wav -'.format(self.source)
        if m == 'CBR':
            enc = 'lame --silent -b {} --cbr - "{}.mp3"'.format(b, o)
        elif m == 'ABR':
            enc = 'lame --silent -b {} --abr - "{}.mp3"'.format(b, o)
        elif m == 'VBR':
            enc = 'lame --silent -V {} - "{}.mp3"'.format(q, o)
        cmd = ' | '.join([ dec, enc ])
        return cmd

    def oggenc(self, o='', m='CBR', b=320, q=4):
        if not o:
            o = self.sname
        dec = 'ffmpeg -i "{}" -f wav -'.format(self.source)
        if m == 'CBR':
            enc = 'oggenc --quiet -b {} --managed -o "{}.ogg" -'.format(b, o)
        elif m == 'ABR':
            enc = 'oggenc --quiet -b {} -o "{}.ogg" -'.format(b, o)
        elif m == 'VBR':
            enc = 'oggenc --quiet -q {} -o "{}.ogg" -'.format(q, o)
        cmd = ' | '.join([ dec, enc ])
        return cmd

# vim: ts=4 sw=4 et:
