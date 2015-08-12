#!/usr/bin/env python3

import os
import subprocess
from collections import OrderedDict
from gi.repository import Gtk

#--Constants--#
VENCS = OrderedDict()
VENCS['AVC (x264)'] = ['x264', 8]
VENCS['AVC (x264, High10)'] = ['x264', 10]
VENCS['HEVC (x265)'] = ['x265', 8]
VENCS['HEVC (x265, Main10)'] = ['x265', 10]
VENCS['HEVC (x265, Main12)'] = ['x265', 12]

ADECS = OrderedDict()
ADECS['DTS-HD (FFmpeg, libdcadec)'] = ['ffmpeg', 'libdcadec']

APROC = OrderedDict()
APROC['SoX Resampler (FFmpeg, libsoxr)'] = ['ffmpeg', 'libsoxr']

AENCS = OrderedDict()
AENCS['AAC (FFmpeg, libfaac)'] = ['ffmpeg', 'libfaac']
AENCS['AAC (faac)'] = ['faac', '']
AENCS['AAC (FFmpeg, libfdk_aac)'] = ['ffmpeg', 'libfdk-aac']
AENCS['AAC (fdkaac)'] = ['fdkaac', '']
AENCS['FLAC (FFmpeg)'] = ['ffmpeg', 'native-flac']
AENCS['FLAC (flac)'] = ['flac', '']
AENCS['MP3 (FFmpeg, libmp3lame)'] = ['ffmpeg', 'libmp3lame']
AENCS['MP3 (lame)'] = ['lame', '']
AENCS['Opus (FFmpeg, libopus)'] = ['ffmpeg', 'libopus']
AENCS['Opus (opusenc)'] = ['opusenc', '']
AENCS['Vorbis (FFmpeg, libvorbis)'] = ['ffmpeg', 'libvorbis']
AENCS['Vorbis (oggenc)'] = ['oggenc', '']

SOURCE_FLTS = OrderedDict()
SOURCE_FLTS['FFMpegSource'] = None
SOURCE_FLTS['LibavSMASHSource'] = None
SOURCE_FLTS['LWLibavSource'] = None

CROP_FLTS = OrderedDict()
CROP_FLTS['CropAbs'] = None
CROP_FLTS['CropRel'] = None

RESIZE_FLTS = OrderedDict()
RESIZE_FLTS['Bilinear'] = None
RESIZE_FLTS['Bicubic'] = None
RESIZE_FLTS['Gauss'] = None
RESIZE_FLTS['Lanczos'] = None
RESIZE_FLTS['Point'] = None
RESIZE_FLTS['Sinc'] = None
RESIZE_FLTS['Spline'] = None

DENOISE_FLTS = OrderedDict()
DENOISE_FLTS['FluxSmoothT'] = None
DENOISE_FLTS['FluxSmoothST'] = None
DENOISE_FLTS['RemoveGrain'] = None
DENOISE_FLTS['TemporalSoften'] = None

DEBAND_FLTS = OrderedDict()
DEBAND_FLTS['f3kdb'] = None

MISC_FLTS = OrderedDict()
MISC_FLTS['Trim'] = None

FILTERS = OrderedDict()
FILTERS['Source'] = SOURCE_FLTS
FILTERS['Crop'] = CROP_FLTS
FILTERS['Resize'] = RESIZE_FLTS
FILTERS['Denoise'] = DENOISE_FLTS
FILTERS['Deband'] = DEBAND_FLTS
FILTERS['Misc'] = MISC_FLTS

#--File Filters--#
sflt = Gtk.FileFilter()
sflt.set_name('VapourSynth scripts')
sflt.add_pattern('*.vpy')

vflt = Gtk.FileFilter()
vflt.set_name('Video files')
for p in ('*.avi', '*.flv', '*.mkv', '*.mp4', '*.ogm'):
    vflt.add_pattern(p)

aflt = Gtk.FileFilter()
aflt.set_name('Audio files')
for p in ('*.aac', '*.ac3', '*.dts', '*.flac', '*.m4a', '*.mka', '*.mp3',
          '*.mpc', '*.ogg', '*.opus', '*.thd', '*.wav', '*.wv'):
    aflt.add_pattern(p)

#--Default Settings--#
vs = [['Source', 'FFMpegSource', OrderedDict()]]

x264 = {'quality': 18,
        'preset': 'medium',
        'tune': 'none',
        'container': '264',
        'arguments': ''}

x265 = {'quality': 18,
        'preset': 'medium',
        'tune': 'none',
        'container': '265',
        'arguments': ''}

audio = {'channel': 0,
         'rate': 0,
         'resampler': 'swr'}

faac = {'mode': 'VBR',
        'bitrate': 128,
        'quality': 100,
        'container': 'm4a'}

fdkaac = {'mode': 'VBR',
          'bitrate': 128,
          'quality': 4,
          'container': 'm4a'}

flac = {'compression': 8,
        'container': 'flac'}

mp3 = {'mode': 'VBR',
       'bitrate': 192,
       'quality': 2,
       'container': 'mp3'}

opus = {'mode': 'VBR',
        'bitrate': 128,
        'container': 'opus'}

vorbis = {'mode': 'VBR',
          'bitrate': 160,
          'quality': 5,
          'container': 'ogg'}

def find_enc(x, y=''):
    path = os.environ['PATH'].split(':')
    for p in path:
        if os.path.isfile('/'.join([p, x])):
            if x.startswith('x264') and not find_x264(x, y):
                return False
            elif x.startswith('x265') and not find_x265(x, y):
                return False
            elif x == 'ffmpeg' and y and not find_ffmpeg(y):
                return False
            else:
                return True
    return False

def find_ffmpeg(y):
    proc = subprocess.Popen('ffmpeg -buildconf',
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL,
                            universal_newlines=True)
    line = proc.stdout.readline()
    while line:
        if '--enable-' + y in line or y.startswith('native'):
            return True
        line = proc.stdout.readline()
    return False

def find_x264(x, y):
    cmd = [x, '--version']
    cmd = ' '.join(cmd)
    proc = subprocess.Popen(cmd,
                            shell=True,
                            stdout=subprocess.PIPE,
                            universal_newlines=True)
    line = proc.stdout.readline()
    while line:
        if '--bit-depth=' + str(y) in line:
            return True
        line = proc.stdout.readline()
    return False

def find_x265(x, y):
    cmd = [x, '--output-depth', str(y), '--version']
    cmd = ' '.join(cmd)
    proc = subprocess.Popen(cmd,
                            shell=True,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)
    line = proc.stderr.readline()
    while line:
        if str(y) + 'bit' in line or str(y) + 'bpp' in line:
            return True
        line = proc.stderr.readline()
    return False

for key in VENCS:
    venc = VENCS[key][0]
    vdepth = VENCS[key][1]
    if not find_enc(venc, vdepth):
        venc = '{}-{}bit'.format(venc, vdepth)
        VENCS[key][0] = venc
        if not find_enc(venc, vdepth):
            VENCS.pop(key)

for key in AENCS:
    aenc = AENCS[key][0]
    alib = AENCS[key][1]
    if not find_enc(aenc, alib):
        AENCS.pop(key)

for key in ADECS:
    adec = ADECS[key][0]
    alib = ADECS[key][1]
    if not find_enc(adec, alib):
        ADECS.pop(key)

for key in APROC:
    aproc = APROC[key][0]
    alib = APROC[key][1]
    if not find_enc(aproc, alib):
        APROC.pop(key)

# vim: ts=4 sw=4 et:
