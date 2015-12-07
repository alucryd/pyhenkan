#!/usr/bin/env python3

from decimal import Decimal


def info(i):
    cmd = 'vspipe "{}" - -i'.format(i)
    return cmd


def preview(i):
    cmd = 'vspipe "{}" /dev/null'.format(i)
    return cmd


def x264(i, o, x, q, p, t, a):
    dec = 'vspipe "{}" - -y'.format(i)
    enc = [x,
           '--crf', str(q),
           '--demuxer', 'y4m']
    if p != 'none':
        enc += ['--preset', p]
    if t != 'none':
        enc += ['--tune', t]
    if a:
        enc.append(a)
    enc += ['--output', '"{}" -'.format(o)]
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd


def x265(i, o, x, d, q, p, t, a):
    dec = 'vspipe "{}" - -y'.format(i)
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
    enc += ['--output', '"{}" -'.format(o)]
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd


def audio_transform(at):
    r, c, n, d, t = at
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


def ffmpeg_libfaac(i, o, t, m, b, q, at):
    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libfaac'.format(i, t)]
    cmd += audio_transform(at)
    if m == 'ABR':
        cmd.append('-b {}'.format(b))
    elif m == 'VBR':
        cmd.append('-q {}'.format(q))
    cmd.append('"{}"'.format(o))
    cmd = ' '.join(cmd)
    return cmd


def faac(i, o, t, m, b, q, at):
    dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, t)]
    dec += audio_transform(at)
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


def ffmpeg_libfdk_aac(i, o, t, m, b, q, at):
    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libfdk_aac'.format(i, t)]
    cmd += audio_transform(at)
    if m == 'CBR':
        cmd.append('-b {}'.format(b))
    elif m == 'VBR':
        cmd.append('-vbr {}'.format(q))
    cmd.append('"{}"'.format(o))
    cmd = ' '.join(cmd)
    return cmd


def fdkaac(i, o, t, m, b, q, at):
    dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, t)]
    dec += audio_transform(at)
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


def ffmpeg_flac(i, o, t, c, at):
    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c flac'.format(i, t)]
    cmd += audio_transform(at)
    cmd.append('-compression_level {}'.format(c))
    cmd.append('"{}"'.format(o))
    cmd = ' '.join(cmd)
    return cmd


def flac(i, o, t, c, at):
    dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, t)]
    dec += audio_transform(at)
    dec.append('-f wav -')
    dec = ' '.join(dec)
    enc = 'flac --silent -{} -o "{}" -'.format(c, o)
    cmd = ' | '.join([dec, enc])
    return cmd


def ffmpeg_libmp3lame(i, o, t, m, b, q, at):
    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libmp3lame'.format(i, t)]
    cmd += audio_transform(at)
    if m == 'CBR':
        cmd.append('-b {}'.format(b))
    elif m == 'ABR':
        cmd.append('-b {} -abr'.format(b))
    elif m == 'VBR':
        cmd.append('-compression_level {}'.format(q))
    cmd.append('"{}"'.format(o))
    cmd = ' '.join(cmd)
    return cmd


def lame(i, o, t, m, b, q, at):
    dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, t)]
    dec += audio_transform(at)
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


def ffmpeg_libopus(i, o, t, m, b, at):
    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libopus'.format(i, t)]
    cmd += audio_transform(at)
    cmd.append('-b {}'.format(b * 1000))
    if m == 'CBR':
        cmd.append('-vbr off')
    elif m == 'ABR':
        cmd.append('-vbr constrained')
    cmd.append('"{}"'.format(o))
    cmd = ' '.join(cmd)
    return cmd


def opusenc(i, o, t, m, b, at):
    dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, t)]
    dec += audio_transform(at)
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


def ffmpeg_libvorbis(i, o, t, m, b, q, at):
    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libvorbis'.format(i, t)]
    cmd += audio_transform(at)
    if m == 'CBR':
        cmd.append('-b {} -m {} -M {}'.format(b, b, b))
    elif m == 'ABR':
        cmd.append('-b {}'.format(b))
    elif m == 'VBR':
        cmd.append('-q {}'.format(q))
    cmd.append('"{}"'.format(o))
    cmd = ' '.join(cmd)
    return cmd


def oggenc(i, o, t, m, b, q, at):
    dec = ['ffmpeg -i "{}" -map 0:{}'.format(i, t)]
    dec += audio_transform(at)
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


def merge(i, o, vt, at=[], st=[], mt=[], uid=''):
    # [[id, filename, title, language]...]
    cmd = ['mkvmerge -o "{}" -D -A -S -B -T "{}"'.format(o, i)]
    if vt:
        v = '-A -S -B -T -M -d {} --no-global-tags --no-chapters '
        v += '--track-name {}:"{}" --language {}:"{}" "{}"'
        v = v.format(vt[0], vt[0], vt[2], vt[0], vt[3], vt[1])
        cmd.append(v)
    if at:
        for t in at:
            a = '-D -S -B -T -M -a {} --no-global-tags --no-chapters '
            a += '--track-name {}:"{}" --language {}:"{}" "{}"'
            a = a.format(t[0], t[0], t[2], t[0], t[3], t[1])
            cmd.append(a)
    if st:
        for t in st:
            s = '-D -A -B -T -M -s {} --no-global-tags --no-chapters '
            s += '--track-name {}:"{}" --language {}:"{}" "{}"'
            s = s.format(t[0], t[0], t[2], t[0], t[3], t[1])
            cmd.append(s)
    if mt:
        for t in mt:
            m = '-D -A -S -T -M -b {} --no-global-tags --no-chapters '
            m += '--track-name {}:"{}" --language {}:"{}" "{}"'
            m = m.format(t[0], t[0], t[2], t[0], t[3], t[1])
            cmd.append(m)
    if uid:
        u = '--segment-uid ' + uid
        cmd.append(u)
    cmd = ' '.join(cmd)
    return cmd

# vim: ts=4 sw=4 et:
