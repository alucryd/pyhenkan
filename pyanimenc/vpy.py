#!/usr/bin/env python3

import pyanimenc.conf as conf

def vpy(source):
    s = []
    s.append('import vapoursynth as vs')
    s.append('core = vs.get_core()')
    for f in conf.filters:
        line = 'clip = core.'
        args = ['clip']
        if f[0] == 'Source':
            if f[1] == 'FFMpegSource':
                line = line + 'ffms2.Source'
            elif f[1] in ['LibavSMASHSource', 'LWLibavSource']:
                line = line + 'lsmas.' + f[1]
            args = ['"{}"'.format(source)]
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
        elif f[0] == 'Misc':
            if f[1] == 'Trim':
                line = line + 'std.' + f[1]
        line = line + '({})'
        if f[2]:
            args = args + ['='.join([key, str(f[2][key])]) for key in f[2]]
        s.append(line.format(', '.join(args)))
    s.append('clip.set_output()')
    s = '\n'.join(s)
    return s

# vim: ts=4 sw=4 et:
