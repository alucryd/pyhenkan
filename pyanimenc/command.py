#!/usr/bin/env python3

def info(i):
    cmd = 'vspipe "{}" - -i'.format(i)
    return cmd

def preview(i):
    dec = 'vspipe "{}" - -y'.format(i)
    enc = 'mpv -'
    cmd = ' | '.join([dec, enc])
    return cmd

def x264(i, o, x='x264', q=18, p='medium', t='none', c='264', a=''):
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
    enc = enc + ['--output', '"{}.{}" -'.format(o, c)]
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd

def x265(i, o, x='x265', d=8, q=18, p='medium', t='none', c='265', a=''):
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
    enc = enc + ['--output', '"{}.{}" -'.format(o, c)]
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd

def ffmpeg_libfaac(i, o, t=0, r=0, c=0, m='VBR', b='128', q=100, co='m4a'):
    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libfaac'.format(i, t)]
    if r:
        cmd.append('-ar {}'.format(r))
    if c:
        cmd.append('-ac {}'.format(c))
    if m == 'ABR':
        cmd.append('-b {}'.format(b))
    elif m == 'VBR':
        cmd.append('-q {}'.format(q))
    cmd.append('"{}.{}"'.format(o, co))
    cmd = ' '.join(cmd)
    return cmd

def faac(i, o, t=0, r=0, c=0, m='VBR', b='128', q=100, co='m4a'):
    dec = 'ffmpeg -i "{}" -map 0:{} -ar {} -ac {} -f wav -'.format(i, t, r, c)
    enc = ['faac']
    if m == 'ABR':
        enc.append('-b {}'.format(b))
    elif m == 'VBR':
        enc.append('-q {}'.format(q))
    enc.append('-o "{}.{}" -'.format(o, c))
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd

def ffmpeg_libfdk_aac(i, o, t=0, r=0, c=0, m='VBR', b='128', q=4, co='m4a'):
    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libfdk_aac'.format(i, t)]
    if r:
        cmd.append('-ar {}'.format(r))
    if c:
        cmd.append('-ac {}'.format(c))
    if m == 'CBR':
        cmd.append('-b {}'.format(b))
    elif m == 'VBR':
        cmd.append('-vbr {}'.format(q))
    cmd.append('"{}.{}"'.format(o, co))
    cmd = ' '.join(cmd)
    return cmd

def fdkaac(i, o, t=0, r=0, c=0, m='VBR', b='128', q=4, co='m4a'):
    dec = 'ffmpeg -i "{}" -map 0:{} -ar {} -ac {} -f caf -'.format(i, t, r, c)
    enc = ['fdkaac --silent']
    if m == 'CBR':
        enc.append('-b {}'.format(b))
    elif m == 'VBR':
        enc.append('-m {}'.format(q))
    enc.append('-o "{}.{}" -'.format(o, co))
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd

def ffmpeg_flac(i, o, t=0, r=0, c=0, cp=8, co='flac'):
    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c flac'.format(i, t)]
    if r:
        cmd.append('-ar {}'.format(r))
    if c:
        cmd.append('-ac {}'.format(c))
    cmd.append('-compression_level {}'.format(cp))
    cmd.append('"{}.{}"'.format(o, co))
    cmd = ' '.join(cmd)
    return cmd

def flac(i, o, t=0, r=0, c=0, cp=8, co='flac'):
    dec = 'ffmpeg -i "{}" -map 0:{} -ar {} -ac {} -f wav -'.format(i, t, r, c)
    enc = 'flac --silent -{} -o "{}.{}" -'.format(cp, o, co)
    cmd = ' | '.join([dec, enc])
    return cmd

def ffmpeg_libmp3lame(i, o, t=0, r=0, c=0, m='VBR', b=192, q=2, co='mp3'):
    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libmp3lame'.format(i, t)]
    if r:
        cmd.append('-ar {}'.format(r))
    if c:
        cmd.append('-ac {}'.format(c))
    if m == 'CBR':
        cmd.append('-b {}'.format(b))
    elif m == 'ABR':
        cmd.append('-b {} -abr'.format(b))
    elif m == 'VBR':
        cmd.append('-compression_level {}'.format(q))
    cmd.append('"{}.{}"'.format(o, co))
    cmd = ' '.join(cmd)
    return cmd

def lame(i, o, t=0, r=0, c=0, m='VBR', b=192, q=2, co='mp3'):
    dec = 'ffmpeg -i "{}" -map 0:{} -ar {} -ac {} -f wav -'.format(i, t, r, c)
    enc = ['lame --silent']
    if m == 'CBR':
        enc.append('-b {} --cbr'.format(b))
    elif m == 'ABR':
        enc.append('-b {} --abr'.format(b))
    elif m == 'VBR':
        enc.append('-V {}'.format(q))
    enc.append('- "{}.{}"'.format(o, co))
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd

def ffmpeg_libopus(i, o, t=0, r=0, c=0, m='VBR', b=128, co='opus'):
    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libopus'.format(i, t)]
    if r:
        cmd.append('-ar {}'.format(r))
    if c:
        cmd.append('-ac {}'.format(c))
    cmd.append('-b {}'.format(b * 1000))
    if m == 'CBR':
        cmd.append('-vbr off')
    elif m == 'ABR':
        cmd.append('-vbr constrained')
    cmd.append('"{}.{}"'.format(o, co))
    cmd = ' '.join(cmd)
    return cmd

def opusenc(i, o, t=0, r=0, c=0, m='VBR', b=128, co='opus'):
    dec = 'ffmpeg -i "{}" -map 0:{} -ar {} -ac {} -f wav -'.format(i, o, r, c)
    enc = ['opusenc --quiet --bitrate {}'.format(b)]
    if m == 'CBR':
        enc.append('--hard-cbr')
    elif m == 'ABR':
        enc.append('--cvbr')
    enc.append('- "{}.{}"'.format(o, co))
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd

def ffmpeg_libvorbis(i, o, t=0, r=0, c=0, m='VBR', b=160, q=5, co='ogg'):
    cmd = ['ffmpeg -y -i "{}" -map 0:{} -c libvorbis'.format(i, t)]
    if r:
        cmd.append('-ar {}'.format(r))
    if c:
        cmd.append('-ac {}'.format(c))
    if m == 'CBR':
        cmd.append('-b {} -m {} -M {}'.format(b, b, b))
    elif m == 'ABR':
        cmd.append('-b {}'.format(b))
    elif m == 'VBR':
        cmd.append('-q {}'.format(q))
    cmd.append('"{}.{}"'.format(o, co))
    cmd = ' '.join(cmd)
    return cmd

def oggenc(i, o, t=0, r=0, c=0, m='VBR', b=160, q=5, co='ogg'):
    dec = 'ffmpeg -i "{}" -map 0:{} -ar {} -ac {} -f wav -'.format(i, t, r, c)
    enc = ['oggenc --quiet -b {}'.format(b)]
    if m == 'CBR':
        enc.append('-b {} --managed -m {} -M {}'.format(b, b, b))
    elif m == 'ABR':
        enc.append('-b {} --managed'.format(b))
    elif m == 'VBR':
        enc.append('-q {}'.format(q))
    enc.append('-o "{}.{}" -'.format(o, co))
    enc = ' '.join(enc)
    cmd = ' | '.join([dec, enc])
    return cmd

def merge(i, o, vt, at=[], st=[], uid=''):
    # [[id, filename, extension, name, language]...]
    x = 'mkvmerge -o "{}" -D -A -S -T "{}"'.format(o, i)
    v = '-A -S -M -T -d {} --no-global-tags --no-chapters '
    v = v + '--track-name {}:"{}" --language {}:"{}" "{}"'
    v = v.format(vt[0], vt[0], vt[3], vt[0], vt[4], vt[1] + '.' + vt[2])
    cmd = [x, v]
    if at:
        for t in at:
            a = '-D -S -M -T -a {} --no-global-tags --no-chapters '
            a = a + '--track-name {}:"{}" --language {}:"{}" "{}"'
            a = a.format(t[0], t[0], t[3], t[0], t[4], t[1] + '.' + t[2])
            cmd.append(a)
    if st:
        for t in st:
            s = '-D -A -M -T -s {} --no-global-tags --no-chapters '
            s = s + '--track-name {}:"{}" --language {}:"{}" "{}"'
            s = s.format(t[0], t[0], t[3], t[0], t[4], t[1] + '.' + t[2])
            cmd.append(s)
    if uid:
        u = '--segment-uid ' + uid
        cmd.append(u)
    cmd = ' '.join(cmd)
    return cmd

# vim: ts=4 sw=4 et:
