#!/usr/bin/env python3

import pyanimenc.conf as conf
from decimal import Decimal

def info(i):
    cmd = 'vspipe "{}" - -i'.format(i)
    return cmd

def preview(i):
    dec = 'vspipe "{}" - -y'.format(i)
    enc = 'mpv -'
    cmd = ' | '.join([dec, enc])
    return cmd

def x264(i, o, x='x264'):
    q = conf.x264['quality']
    p = conf.x264['preset']
    t = conf.x264['tune']
    a = conf.x264['arguments']

    dec = 'vspipe "{}" - -y'.format(i)
    enc = [x,
           '--crf', str(q),
           '--demuxer', 'y4m']
    if p != 'none':
        enc = enc + ['--preset', p]
    if t != 'none':
        enc = enc + ['--tune', t]
    if a:
        enc.append(a)
    enc = enc + ['--output', '"{}" -'.format(o)]
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd

def x265(i, o, x='x265', d=8):
    q = conf.x265['quality']
    p = conf.x265['preset']
    t = conf.x265['tune']
    a = conf.x265['arguments']

    dec = 'vspipe "{}" - -y'.format(i)
    enc = [x,
           '--output-depth', str(d),
           '--crf', str(q),
           '--y4m']
    if p != 'none':
        enc = enc + ['--preset', p]
    if t != 'none':
        enc = enc + ['--tune', t]
    if a:
        enc.append(a)
    enc = enc + ['--output', '"{}" -'.format(o)]
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd

def audio_transform():
    r = conf.audio['rate']
    c = conf.audio['channel']
    n = conf.video['fpsnum']
    d = conf.video['fpsden']
    t = conf.trim

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

def ffmpeg_libfaac(i, o, t=0):
    m = conf.faac['mode']
    b = conf.faac['bitrate']
    q = conf.faac['quality']

    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libfaac'.format(i, t)]
    cmd = cmd + audio_transform()
    if m == 'ABR':
        cmd.append('-b {}'.format(b))
    elif m == 'VBR':
        cmd.append('-q {}'.format(q))
    cmd.append('"{}"'.format(o))
    cmd = ' '.join(cmd)
    return cmd

def faac(i, o, t=0):
    m = conf.faac['mode']
    b = conf.faac['bitrate']
    q = conf.faac['quality']

    dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, t)]
    dec = dec + audio_transform()
    dec.append('-f wav -')
    dec = ' '.join(dec)
    enc = ['faac']
    if m == 'ABR':
        enc.append('-b {}'.format(b))
    elif m == 'VBR':
        enc.append('-q {}'.format(q))
    enc.append('-o "{}" -'.format(o))
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd

def ffmpeg_libfdk_aac(i, o, t=0):
    m = conf.fdkaac['mode']
    b = conf.fdkaac['bitrate']
    q = conf.fdkaac['quality']

    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libfdk_aac'.format(i, t)]
    cmd = cmd + audio_transform()
    if m == 'CBR':
        cmd.append('-b {}'.format(b))
    elif m == 'VBR':
        cmd.append('-vbr {}'.format(q))
    cmd.append('"{}"'.format(o))
    cmd = ' '.join(cmd)
    return cmd

def fdkaac(i, o, t=0):
    m = conf.fdkaac['mode']
    b = conf.fdkaac['bitrate']
    q = conf.fdkaac['quality']

    dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, t)]
    dec = dec + audio_transform()
    dec.append('-f caf -')
    dec = ' '.join(dec)
    enc = ['fdkaac --silent']
    if m == 'CBR':
        enc.append('-b {}'.format(b))
    elif m == 'VBR':
        enc.append('-m {}'.format(q))
    enc.append('-o "{}" -'.format(o))
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd

def ffmpeg_flac(i, o, t=0):
    c = conf.flac['compression']

    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c flac'.format(i, t)]
    cmd = cmd + audio_transform()
    cmd.append('-compression_level {}'.format(c))
    cmd.append('"{}"'.format(o))
    cmd = ' '.join(cmd)
    return cmd

def flac(i, o, t=0):
    c = conf.flac['compression']

    dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, t)]
    dec = dec + audio_transform()
    dec.append('-f wav -')
    dec = ' '.join(dec)
    enc = 'flac --silent -{} -o "{}" -'.format(c, o)
    cmd = ' | '.join([dec, enc])
    return cmd

def ffmpeg_libmp3lame(i, o, t=0):
    m = conf.mp3['mode']
    b = conf.mp3['bitrate']
    q = conf.mp3['quality']

    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libmp3lame'.format(i, t)]
    cmd = cmd + audio_transform()
    if m == 'CBR':
        cmd.append('-b {}'.format(b))
    elif m == 'ABR':
        cmd.append('-b {} -abr'.format(b))
    elif m == 'VBR':
        cmd.append('-compression_level {}'.format(q))
    cmd.append('"{}"'.format(o))
    cmd = ' '.join(cmd)
    return cmd

def lame(i, o, t=0):
    m = conf.mp3['mode']
    b = conf.mp3['bitrate']
    q = conf.mp3['quality']

    dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, t)]
    dec = dec + audio_transform()
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

def ffmpeg_libopus(i, o, t=0):
    m = conf.opus['mode']
    b = conf.opus['bitrate']

    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libopus'.format(i, t)]
    cmd = cmd + audio_transform()
    cmd.append('-b {}'.format(b * 1000))
    if m == 'CBR':
        cmd.append('-vbr off')
    elif m == 'ABR':
        cmd.append('-vbr constrained')
    cmd.append('"{}"'.format(o))
    cmd = ' '.join(cmd)
    return cmd

def opusenc(i, o, t=0):
    m = conf.opus['mode']
    b = conf.opus['bitrate']

    dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, t)]
    dec = dec + audio_transform()
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

def ffmpeg_libvorbis(i, o, t=0):
    m = conf.vorbis['mode']
    b = conf.vorbis['bitrate']
    q = conf.vorbis['quality']

    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libvorbis'.format(i, t)]
    cmd = cmd + audio_transform()
    if m == 'CBR':
        cmd.append('-b {} -m {} -M {}'.format(b, b, b))
    elif m == 'ABR':
        cmd.append('-b {}'.format(b))
    elif m == 'VBR':
        cmd.append('-q {}'.format(q))
    cmd.append('"{}"'.format(o))
    cmd = ' '.join(cmd)
    return cmd

def oggenc(i, o, t=0):
    m = conf.vorbis['mode']
    b = conf.vorbis['bitrate']
    q = conf.vorbis['quality']

    dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, t)]
    dec = dec + audio_transform()
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

def merge(i, o, vt, at=[], st=[], uid=''):
    # [[id, filename, title, language]...]
    cmd = ['mkvmerge -o "{}" -D -A -S -T "{}"'.format(o, i)]
    if vt:
        v = '-A -S -M -T -d {} --no-global-tags --no-chapters '
        v = v + '--track-name {}:"{}" --language {}:"{}" "{}"'
        v = v.format(vt[0], vt[0], vt[2], vt[0], vt[3], vt[1])
        cmd.append(v)
    if at:
        for t in at:
            a = '-D -S -M -T -a {} --no-global-tags --no-chapters '
            a = a + '--track-name {}:"{}" --language {}:"{}" "{}"'
            a = a.format(t[0], t[0], t[2], t[0], t[3], t[1])
            cmd.append(a)
    if st:
        for t in st:
            s = '-D -A -M -T -s {} --no-global-tags --no-chapters '
            s = s + '--track-name {}:"{}" --language {}:"{}" "{}"'
            s = s.format(t[0], t[0], t[2], t[0], t[3], t[1])
            cmd.append(s)
    if uid:
        u = '--segment-uid ' + uid
        cmd.append(u)
    cmd = ' '.join(cmd)
    return cmd

# vim: ts=4 sw=4 et:
