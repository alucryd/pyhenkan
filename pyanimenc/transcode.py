import re
import subprocess

import pyanimenc.conf as conf
from pyanimenc.queue import Queue
from pyanimenc.vapoursynth import VapourSynthScript

from decimal import Decimal
from gi.repository import GLib


class Transcode:
    def __init__(self, track, pbar):
        self.track = track
        self.pbar = pbar
        self.queue = Queue()

    def script(self, vpy, filters):
        print('Create VapourSynth script...')
        t = self.track
        s = VapourSynthScript().script(t.file.path, filters)

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
        subprocess.run(cmd, shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       universal_newlines=True)

    def video(self, codec):
        print('Encode video...')
        t = self.track
        o = '/'.join([t.file.tmpd, t.file.name])

        if codec[0].startswith('x264'):
            cfg = conf.x264
            cmd = self._x264(o, codec[0],
                             cfg['container'],
                             cfg['quality'],
                             cfg['preset'],
                             cfg['tune'],
                             cfg['arguments'])
        elif codec[0].startswith('x265'):
            cfg = conf.x265
            cmd = self._x265(o, codec[0], codec[1],
                             cfg['container'],
                             cfg['quality'],
                             cfg['preset'],
                             cfg['tune'],
                             cfg['arguments'])

        print(cmd)

        self.queue.proc = subprocess.Popen(cmd, shell=True,
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.PIPE,
                                           universal_newlines=True)
        self._video_progress()

        t.tmpfilepath = '.'.join([o, cfg['container']])
        t.id = 0

    def audio(self, codec, filters):
        print('Encode audio...')
        t = self.track
        i = t.file.path
        o = '_'.join([t.file.name, str(t.id)])
        o = '/'.join([t.file.tmpd, o])
        n = t.id
        f = filters

        if t.codec[0] == 'ffmpeg':
            cfg, cmd = self._ffmpeg(codec[1], i, o, n, f)

        elif t.codec[0] == 'faac':
            cfg = conf.faac
            cmd = self._faac(i, o, n, f,
                             cfg['container'],
                             cfg['mode'],
                             cfg['bitrate'],
                             cfg['quality'])

        elif t.codec[0] == 'fdkaac':
            cfg = conf.fdkaac
            cmd = self._fdkaac(i, o, n, f,
                               cfg['container'],
                               cfg['mode'],
                               cfg['bitrate'],
                               cfg['quality'])

        elif t.codec[0] == 'flac':
            cfg = conf.flac
            cmd = self._native_flac(i, o, n, f,
                                    cfg['container'],
                                    cfg['compression'])

        elif t.codec[0] == 'lame':
            cfg = conf.mp3
            cmd = self._lame(i, o, n, f,
                             cfg['container'],
                             cfg['mode'],
                             cfg['bitrate'],
                             cfg['quality'])

        elif t.codec[0] == 'opusenc':
            cfg = conf.opus
            cmd = self._opusenc(i, o, n, f,
                                cfg['container'],
                                cfg['mode'],
                                cfg['bitrate'])

        elif t.codec[0] == 'oggenc':
            cfg = conf.vorbis
            cmd = self._oggenc(i, o, n, f,
                               cfg['container'],
                               cfg['mode'],
                               cfg['bitrate'],
                               cfg['quality'])

        print(cmd)

        self.queue.proc = subprocess.Popen(cmd, shell=True,
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.PIPE,
                                           universal_newlines=True)
        self._audio_progress()

        t.tmpfilepath = '.'.join([o, cfg['container']])
        t.id = 0

    def _x264(self, o, x, e, q, p, t, a):
        dec = 'vspipe "{}" - -y'.format(self.vpy)
        enc = [x,
               '--crf', str(q),
               '--demuxer', 'y4m']
        if p != 'none':
            enc += ['--preset', p]
        if t != 'none':
            enc += ['--tune', t]
        if a:
            enc.append(a)
        enc += ['--output', '"{}.{}" -'.format(o, e)]
        enc = ' '.join(enc)
        cmd = ' | '.join([dec, enc])

        return cmd

    def _x265(self, o, x, d, e, q, p, t, a):
        dec = 'vspipe "{}" - -y'.format(self.vpy)
        enc = [x,
               '--output-depth', str(d),
               '--crf', str(q),
               '--y4m']
        if p != 'none':
            enc += ['--preset', p]
        if t != 'none':
            enc += ['--tune', t]
        if a:
            enc.append(a)
        enc += ['--output', '"{}.{}" -'.format(o, e)]
        enc = ' '.join(enc)
        cmd = ' | '.join([dec, enc])

        return cmd

    def _video_progress(self):
        GLib.idle_add(self.pbar.set_fraction, 0)
        GLib.idle_add(self.pbar.set_text, 'Encoding video...')

        self.queue.update()

        proc = self.queue.proc
        d = self._info()
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

    def _ffmpeg(self, l, i, o, n, f):
        if l == 'libfaac':
            cfg = conf.faac
            cmd = self._libfaac(i, o, n, f,
                                cfg['container'],
                                cfg['mode'],
                                cfg['bitrate'],
                                cfg['quality'])

        elif l == 'libfdk-aac':
            cfg = conf.fdkaac
            cmd = self._libfdk_aac(i, o, n, f,
                                   cfg['container'],
                                   cfg['mode'],
                                   cfg['bitrate'],
                                   cfg['quality'])

        elif l == 'native-flac':
            cfg = conf.flac
            cmd = self._native_flac(i, o, n, f,
                                    cfg['container'],
                                    cfg['compression'])

        elif l == 'libmp3lame':
            cfg = conf.mp3
            cmd = self._libmp3lame(i, o, n, f,
                                   cfg['container'],
                                   cfg['mode'],
                                   cfg['bitrate'],
                                   cfg['quality'])

        elif l == 'libopus':
            cfg = conf.opus
            cmd = self._libopus(i, o, n, f,
                                cfg['container'],
                                cfg['mode'],
                                cfg['bitrate'])

        elif l == 'libvorbis':
            cfg = conf.vorbis
            cmd = self._libvorbis(i, o, n, f,
                                  cfg['container'],
                                  cfg['mode'],
                                  cfg['bitrate'],
                                  cfg['quality'])

        return cfg, cmd

    def _libfaac(self, i, o, n, f, e, m, b, q):
        cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libfaac'.format(i, n)]
        cmd += self._audio_transform(f)
        if m == 'ABR':
            cmd.append('-b {}'.format(b))
        elif m == 'VBR':
            cmd.append('-q {}'.format(q))
        cmd.append('"{}.{}"'.format(o, e))
        cmd = ' '.join(cmd)

        return cmd

    def _faac(self, i, o, n, f, e, m, b, q):
        dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, n)]
        dec += self._audio_transform(f)
        dec.append('-f wav -')
        dec = ' '.join(dec)
        enc = ['faac']
        if m == 'ABR':
            enc.append('-b {}'.format(b))
        elif m == 'VBR':
            enc.append('-q {}'.format(q))
        enc.append('-o "{}.{}" -'.format(o, e))
        enc = ' '.join(enc)
        cmd = ' | '.join([dec, enc])

        return cmd

    def _libfdk_aac(self, i, o, n, f, e, m, b, q):
        cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libfdk_aac'.format(i, n)]
        cmd += self._audio_transform(f)
        if m == 'CBR':
            cmd.append('-b {}'.format(b))
        elif m == 'VBR':
            cmd.append('-vbr {}'.format(q))
        cmd.append('"{}.{}"'.format(o, e))
        cmd = ' '.join(cmd)

        return cmd

    def _fdkaac(self, i, o, n, f, e, m, b, q):
        dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, n)]
        dec += self._audio_transform(f)
        dec.append('-f caf -')
        dec = ' '.join(dec)
        enc = ['fdkaac --silent']
        if m == 'CBR':
            enc.append('-b {}'.format(b))
        elif m == 'VBR':
            enc.append('-m {}'.format(q))
        enc.append('-o "{}.{}" -'.format(o, e))
        enc = ' '.join(enc)
        cmd = ' | '.join([dec, enc])

        return cmd

    def _native_flac(self, i, o, n, f, e, c):
        cmd = ['ffmpeg -y -i "{}" -map 0:{} -c flac'.format(i, n)]
        cmd += self._audio_transform(f)
        cmd.append('-compression_level {}'.format(c))
        cmd.append('"{}.{}"'.format(o, e))
        cmd = ' '.join(cmd)

        return cmd

    def _flac(self, i, o, n, f, e, c):
        dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, n)]
        dec += self._audio_transform(f)
        dec.append('-f wav -')
        dec = ' '.join(dec)
        enc = 'flac --silent -{} -o "{}.{}" -'.format(c, o, e)
        cmd = ' | '.join([dec, enc])

        return cmd

    def _libmp3lame(self, i, o, n, f, e, m, b, q):
        cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libmp3lame'.format(i, n)]
        cmd += self._audio_transform(f)
        if m == 'CBR':
            cmd.append('-b {}'.format(b))
        elif m == 'ABR':
            cmd.append('-b {} -abr'.format(b))
        elif m == 'VBR':
            cmd.append('-compression_level {}'.format(q))
        cmd.append('"{}.{}"'.format(o, e))
        cmd = ' '.join(cmd)

        return cmd

    def _lame(self, i, o, n, f, e, m, b, q):
        dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, n)]
        dec += self._audio_transform(f)
        dec.append('-f wav -')
        dec = ' '.join(dec)
        enc = ['lame --silent']
        if m == 'CBR':
            enc.append('-b {} --cbr'.format(b))
        elif m == 'ABR':
            enc.append('-b {} --abr'.format(b))
        elif m == 'VBR':
            enc.append('-V {}'.format(q))
        enc.append('- "{}"'.format(o))
        enc = ' '.join(enc)
        cmd = ' | '.join([dec, enc])

        return cmd

    def _libopus(self, i, o, n, f, e, m, b):
        cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libopus'.format(i, n)]
        cmd += self._audio_transform(f)
        cmd.append('-b {}'.format(b * 1000))
        if m == 'CBR':
            cmd.append('-vbr off')
        elif m == 'ABR':
            cmd.append('-vbr constrained')
        cmd.append('"{}"'.format(o))
        cmd = ' '.join(cmd)

        return cmd

    def _opusenc(self, i, o, n, f, e, m, b):
        dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, n)]
        dec += self._audio_transform(f)
        dec.append('-f wav -')
        dec = ' '.join(dec)
        enc = ['opusenc --quiet --bitrate {}'.format(b)]
        if m == 'CBR':
            enc.append('--hard-cbr')
        elif m == 'ABR':
            enc.append('--cvbr')
        enc.append('- "{}"'.format(o))
        enc = ' '.join(enc)
        cmd = ' | '.join([dec, enc])

        return cmd

    def _libvorbis(self, i, o, n, f, e, m, b, q):
        cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libvorbis'.format(i, n)]
        cmd += self._audio_transform(f)
        if m == 'CBR':
            cmd.append('-b {} -m {} -M {}'.format(b, b, b))
        elif m == 'ABR':
            cmd.append('-b {}'.format(b))
        elif m == 'VBR':
            cmd.append('-q {}'.format(q))
        cmd.append('"{}"'.format(o))
        cmd = ' '.join(cmd)

        return cmd

    def _oggenc(self, i, o, n, f, e, m, b, q):
        dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, n)]
        dec += self._audio_transform(f)
        dec.append('-f wav -')
        dec = ' '.join(dec)
        enc = ['oggenc --quiet -b {}'.format(b)]
        if m == 'CBR':
            enc.append('-b {} --managed -m {} -M {}'.format(b, b, b))
        elif m == 'ABR':
            enc.append('-b {} --managed'.format(b))
        elif m == 'VBR':
            enc.append('-q {}'.format(q))
        enc.append('-o "{}" -'.format(o))
        enc = ' '.join(enc)
        cmd = ' | '.join([dec, enc])

        return cmd

    def _audio_transform(self, f):
        r, c, n, d, t = f
        cmd = []

        if r:
            cmd.append('-ar {}'.format(r))
        if c:
            cmd.append('-ac {}'.format(c))
        if t != [0, 0] and (n != 0 or d != 1):
            f = Decimal(t[0]) * Decimal(d) / Decimal(n)
            l = Decimal(t[1] + 1) * Decimal(d) / Decimal(n)
            cmd.append('-af atrim={}:{}'.format(f, l))

        return cmd

    def _audio_progress(self):
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

# vim: ts=4 sw=4 et:
