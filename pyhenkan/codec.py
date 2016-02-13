import io
import subprocess
import sys

from collections import OrderedDict
from decimal import Decimal

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class Codec:
    def __init__(self, library, dialog):
        self.library = library
        self.dialog = dialog
        self.arguments = ''

    def is_avail(self):
        if sys.version_info < (3, 5):
            proc = subprocess.Popen(['ffmpeg', '-codecs'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL,
                                    universal_newlines=True)
            buf = proc.stdout
        else:
            proc = subprocess.run(['ffmpeg', '-codecs'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  universal_newlines=True)
            buf = io.StringIO(proc.stdout + proc.stderr)
        line = buf.readline()
        while line:
            if self.library in line or not self.library.startswith('lib'):
                return True
            line = buf.readline()
        return False

    def show_dialog(self, parent):
        dlg = self.dialog(self, parent)
        dlg.run()
        dlg.destroy()


class VideoCodec(Codec):
    def __init__(self, library, dialog):
        Codec.__init__(self, library, dialog)
        self.pixel_format = 'auto'
        self.color_matrix = ['auto', 'auto']

    def get_cmd(self, input, output, settings):
        dec = ['vspipe', "{}".format(input), '-', '-y']
        enc = ['ffmpeg', '-y', '-i -', '-c:v', self.library]
        if self.pixel_format != 'auto':
            enc += ['-pix_fmt', self.pixel_format]
        if self.color_matrix != ['auto', 'auto']:
            enc += ['-vf', 'colormatrix={}:{}'.format(self.color_matrix[0],
                                                      self.color_matrix[1])]
        enc += settings
        if self.arguments:
            enc += [self.arguments]
        enc += ['"{}.{}"'.format(output, self.container)]
        cmd = dec + ['|'] + enc
        return cmd


class Vpx(VideoCodec):
    def __init__(self, library, dialog):
        VideoCodec.__init__(self, library, dialog)
        self.crf = 10
        self.preset = 'good'
        self.cpu_used = 2
        self.container = 'webm'

    def get_cmd(self, input, output):
        settings = ['-crf', str(self.crf),
                    '-b:v', str(0),
                    '-quality', self.preset]
        if self.preset != 'best':
            settings += ['-cpu-used', str(self.cpu_used)]
        cmd = super().get_cmd(input, output, settings)
        return cmd


class Vp8(Vpx):
    def __init__(self):
        Vpx.__init__(self, 'libvpx', Vp8Dialog)


class Vp9(Vpx):
    def __init__(self):
        Vpx.__init__(self, 'libvpx-vp9', Vp9Dialog)


class X264(VideoCodec):
    def __init__(self):
        VideoCodec.__init__(self, 'libx264', X264Dialog)
        self.crf = 18
        self.preset = 'medium'
        self.tune = 'none'
        self.container = 'mp4'

    def get_cmd(self, input, output):
        settings = ['-crf', str(self.crf)]
        if self.preset != 'none':
            settings += ['-preset', self.preset]
        if self.tune != 'none':
            settings += ['-tune', self.tune]
        cmd = super().get_cmd(input, output, settings)
        return cmd


class X265(VideoCodec):
    def __init__(self):
        VideoCodec.__init__(self, 'libx265', X265Dialog)
        self.crf = 18
        self.preset = 'medium'
        self.container = 'mp4'

    def get_cmd(self, input, output):
        settings = ['-crf', str(self.crf)]
        if self.preset != 'none':
            settings += ['-preset', self.preset]
        cmd = super().get_cmd(input, output, settings)
        return cmd


class AudioCodec(Codec):
    def __init__(self, library, dialog):
        Codec.__init__(self, library, dialog)
        self.channel = 0
        self.rate = 0
        self.resampler = 'swr'

    # Try to get rid of all those track.file
    def get_cmd(self, track, output, settings):
        cmd = ['ffmpeg', '-y']
        if track.format == 'DTS' and Dcadec.is_avail():
            cmd += ['-c:a', 'libdcadec']
        cmd += ['-i', track.file.path,
                '-map 0:{}'.format(track.id),
                '-c:a', self.library]
        if self.channel != track.channel:
            cmd += ['-ac', str(self.channel)]
        if self.rate != track.rate:
            cmd += ['-ar', str(self.rate)]
        if self.resampler != 'swr':
            cmd += ['-af', 'aresample=resampler={}'.format(self.resampler)]
        t = [track.file.first, track.file.last]
        n = track.file.fpsnum
        d = track.file.fpsden
        if t != [0, 0] and [n, d] != [0, 1]:
            f = Decimal(t[0]) * Decimal(d) / Decimal(n)
            l = Decimal(t[1] + 1) * Decimal(d) / Decimal(n)
            cmd += ['-af atrim={}:{}'.format(f, l)]
        cmd += settings
        cmd += ['"{}.{}"'.format(output, self.container)]
        return cmd


class Aac(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'aac', AacDialog)
        self.mode = 'CBR'
        self.bitrate = 128
        self.container = 'm4a'

    def get_cmd(self, track, output):
        settings = ['-strict', '-2', '-b:a', str(self.bitrate) + 'k']
        cmd = super().get_cmd(track, output, settings)
        return cmd


class Faac(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'libfaac', FaacDialog)
        self.mode = 'VBR'
        self.bitrate = 128
        self.quality = 100
        self.container = 'm4a'

    def get_cmd(self, track, output):
        if self.mode == 'ABR':
            settings = ['-b:a', str(self.bitrate) + 'k']
        elif self.mode == 'VBR':
            settings = ['-q:a', str(self.quality)]
        cmd = super().get_cmd(track, output, settings)
        return cmd


class Fdkaac(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'libfdk_aac', FdkaacDialog)
        self.mode = 'VBR'
        self.bitrate = 128
        self.quality = 4
        self.container = 'm4a'

    def get_cmd(self, track, output):
        if self.mode == 'CBR':
            settings = ['-b:a', str(self.bitrate) + 'k']
        elif self.mode == 'VBR':
            settings = ['-q:a', str(self.quality)]
        cmd = super().get_cmd(track, output, settings)
        return cmd


class Flac(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'flac', FlacDialog)
        self.container = 'flac'

    def get_cmd(self, track, output):
        cmd = super().get_cmd(track, output, [])
        return cmd


class Lame(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'libmp3lame', LameDialog)
        self.mode = 'VBR'
        self.bitrate = 192
        self.quality = 2
        self.container = 'mp3'

    def get_cmd(self, track, output):
        if self.mode in ['CBR', 'ABR']:
            settings = ['-b:a', str(self.bitrate) + 'k']
        elif self.mode == 'VBR':
            settings = ['-q:a', str(self.quality)]
        if self.mode == 'ABR':
            settings += ['-abr']
        cmd = super().get_cmd(track, output, settings)
        return cmd


class Opus(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'libopus', OpusDialog)
        self.mode = 'VBR'
        self.bitrate = 128
        self.container = 'opus'

    def get_cmd(self, track, output):
        settings = ['-b:a', str(self.bitrate) + 'k']
        if self.mode == 'CBR':
            settings += ['-vbr off']
        elif self.mode == 'ABR':
            settings += ['-vbr constrained']
        cmd = super().get_cmd(track, output, settings)
        return cmd


class Vorbis(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'libvorbis', VorbisDialog)
        self.mode = 'VBR'
        self.bitrate = 160
        self.quality = 3
        self.container = 'ogg'

    def get_cmd(self, track, output):
        if self.mode == 'ABR':
            settings = ['-b:a', str(self.bitrate) + 'k']
        elif self.mode == 'VBR':
            settings = ['-q:a', str(self.quality)]
        cmd = super().get_cmd(track, output, settings)
        return cmd


class Dcadec(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'libdcadec', None)


class Swr(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'swr', None)


class Soxr(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'libsoxr', None)


class CodecDialog(Gtk.Dialog):
    def __init__(self, codec, parent):
        Gtk.Dialog.__init__(self, codec.library, parent, Gtk.DialogFlags.MODAL)
        self.set_default_size(240, 0)

        self.codec = codec

        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(6)
        self.grid.set_row_spacing(6)
        self.grid.set_property('margin', 6)

        box = self.get_content_area()
        box.add(self.grid)

    def crf(self, crfs):
        self.crf_label = Gtk.Label('CRF')
        self.crf_label.set_halign(Gtk.Align.START)

        self.crf_spin = Gtk.SpinButton()
        self.crf_spin.set_property('hexpand', True)
        self.crf_spin.set_numeric(True)
        self.crf_spin.set_adjustment(crfs)
        self.crf_spin.set_value(self.codec.crf)
        self.crf_spin.connect('value-changed', self.on_crf_changed)

    def preset(self, presets):
        self.preset_label = Gtk.Label('Preset')
        self.preset_label.set_halign(Gtk.Align.START)

        self.preset_cbtext = Gtk.ComboBoxText()
        self.preset_cbtext.set_property('hexpand', True)
        for p in presets:
            self.preset_cbtext.append_text(p)
        i = presets.index(self.codec.preset)
        self.preset_cbtext.set_active(i)
        self.preset_cbtext.connect('changed', self.on_preset_changed)

    def tune(self, tunes):
        self.tune_label = Gtk.Label('Tune')
        self.tune_label.set_halign(Gtk.Align.START)

        self.tune_cbtext = Gtk.ComboBoxText()
        self.tune_cbtext.set_property('hexpand', True)
        for t in tunes:
            self.tune_cbtext.append_text(t)
        i = tunes.index(self.codec.tune)
        self.tune_cbtext.set_active(i)
        self.tune_cbtext.connect('changed', self.on_tune_changed)

    def cpu_used(self, cpus_used):
        self.cpu_used_label = Gtk.Label('CPU Used')
        self.cpu_used_label.set_halign(Gtk.Align.START)

        self.cpu_used_spin = Gtk.SpinButton()
        self.cpu_used_spin.set_property('hexpand', True)
        self.cpu_used_spin.set_numeric(True)
        self.cpu_used_spin.set_adjustment(cpus_used)
        self.cpu_used_spin.set_value(self.codec.cpu_used)
        self.cpu_used_spin.connect('value-changed', self.on_cpu_used_changed)

    def arguments(self):
        self.arguments_label = Gtk.Label('Custom arguments')
        self.arguments_label.set_halign(Gtk.Align.CENTER)

        self.arguments_entry = Gtk.Entry()
        self.arguments_entry.set_property('hexpand', True)
        self.arguments_entry.set_text(self.codec.arguments)
        self.arguments_entry.connect('changed', self.on_arguments_changed)

    def pixel_format(self):
        pixel_formats = OrderedDict()
        pixel_formats['Auto'] = 'auto'
        pixel_formats['YUV 4:2:0 8bit'] = 'yuv420p'
        pixel_formats['YUV 4:2:2 8bit'] = 'yuv422p'
        pixel_formats['YUV 4:4:4 8bit'] = 'yuv444p'
        pixel_formats['YUV 4:2:0 10bit'] = 'yuv420p10le'
        pixel_formats['YUV 4:2:2 10bit'] = 'yuv422p10le'
        pixel_formats['YUV 4:4:4 10bit'] = 'yuv444p10le'
        pixel_formats['YUV 4:2:0 12bit'] = 'yuv420p12le'
        pixel_formats['YUV 4:2:2 12bit'] = 'yuv422p12le'
        pixel_formats['YUV 4:4:4 12bit'] = 'yuv444p12le'

        self.pixel_format_label = Gtk.Label('Pixel Format')
        self.pixel_format_label.set_halign(Gtk.Align.START)

        self.pixel_format_cbtext = Gtk.ComboBoxText()
        self.pixel_format_cbtext.set_property('hexpand', True)
        for p in pixel_formats:
            self.pixel_format_cbtext.append_text(p)

        i = 0
        for pf in pixel_formats:
            if pixel_formats[pf] == self.codec.pixel_format:
                self.pixel_format_cbtext.set_active(i)
            else:
                i += 1

        self.pixel_format_cbtext.connect('changed',
                                         self.on_pixel_format_changed,
                                         pixel_formats)

    def color_matrix(self):
        color_matrices = OrderedDict()
        color_matrices['Auto'] = 'auto'
        color_matrices['BT.709'] = 'bt709'
        color_matrices['BT.601'] = 'bt601'
        color_matrices['SMPTE-240M'] = 'smpte240m'
        color_matrices['FCC'] = 'fcc'

        self.input_matrix_label = Gtk.Label('Input Matrix')
        self.input_matrix_label.set_halign(Gtk.Align.START)
        self.output_matrix_label = Gtk.Label('Output Matrix')
        self.output_matrix_label.set_halign(Gtk.Align.START)

        self.input_matrix_cbtext = Gtk.ComboBoxText()
        self.input_matrix_cbtext.set_property('hexpand', True)
        self.output_matrix_cbtext = Gtk.ComboBoxText()
        self.output_matrix_cbtext.set_property('hexpand', True)
        for cm in color_matrices:
            self.input_matrix_cbtext.append_text(cm)
            self.output_matrix_cbtext.append_text(cm)

        i = 0
        for cm in color_matrices:
            if color_matrices[cm] in self.codec.color_matrix:
                if color_matrices[cm] == self.codec.color_matrix[0]:
                    self.input_matrix_cbtext.set_active(i)
                if color_matrices[cm] == self.codec.color_matrix[1]:
                    self.output_matrix_cbtext.set_active(i)
            else:
                i += 1

        self.input_matrix_cbtext.connect('changed',
                                         self.on_color_matrix_changed,
                                         0, color_matrices)
        self.output_matrix_cbtext.connect('changed',
                                          self.on_color_matrix_changed,
                                          1, color_matrices)

    def mode(self, modes):
        self.mode_label = Gtk.Label('Mode')
        self.mode_label.set_halign(Gtk.Align.START)

        self.mode_cbtext = Gtk.ComboBoxText()
        self.mode_cbtext.set_property('hexpand', True)
        for m in modes:
            self.mode_cbtext.append_text(m)
        i = modes.index(self.codec.mode)
        self.mode_cbtext.set_active(i)
        self.mode_cbtext.connect('changed', self.on_mode_changed)

    def bitrate(self, bitrates):
        self.bitrate_label = Gtk.Label('Bitrate')
        self.bitrate_label.set_halign(Gtk.Align.START)

        self.bitrate_spin = Gtk.SpinButton()
        self.bitrate_spin.set_property('hexpand', True)
        self.bitrate_spin.set_numeric(True)
        self.bitrate_spin.set_adjustment(bitrates)
        self.bitrate_spin.set_value(self.codec.bitrate)
        self.bitrate_spin.connect('value-changed', self.on_bitrate_changed)

    def quality(self, qualities):
        self.quality_label = Gtk.Label('Quality')
        self.quality_label.set_halign(Gtk.Align.START)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(qualities)
        self.quality_spin.set_value(self.codec.quality)
        self.quality_spin.connect('value-changed', self.on_quality_changed)

    def channel(self):
        channels = OrderedDict()
        channels['1.0'] = 1
        channels['2.0'] = 2
        if self.codec.library not in ('libmp3lame'):
            channels['2.1'] = 3
            channels['4.0'] = 4
            channels['5.0'] = 5
            channels['5.1'] = 6
            channels['6.1'] = 7
            channels['7.1'] = 8

        self.channel_label = Gtk.Label('Channels')
        self.channel_label.set_halign(Gtk.Align.START)

        self.channel_cbtext = Gtk.ComboBoxText()
        self.channel_cbtext.set_property('hexpand', True)
        for c in channels:
            self.channel_cbtext.append_text(c)

        i = 0
        for c in channels:
            if channels[c] == self.codec.channel:
                self.channel_cbtext.set_active(i)
            else:
                i += 1

        self.channel_cbtext.connect('changed', self.on_channel_changed,
                                    channels)

    def rate(self):
        rates = OrderedDict()
        rates['8 kHz'] = 8000
        if self.codec.library not in ('libopus'):
            rates['11.025 kHz'] = 11025
        rates['16 kHz'] = 16000
        if self.codec.library not in ('libopus'):
            rates['22.05 kHz'] = 22050
        rates['24 kHz'] = 24000
        if self.codec.library not in ('libopus'):
            rates['32 kHz'] = 32000
        if self.codec.library not in ('libopus'):
            rates['44.1 kHz'] = 44100
        rates['48 kHz'] = 48000
        if self.codec.library not in ('libmp3lame', 'libopus'):
            rates['64 kHz'] = 64000
        if self.codec.library not in ('libmp3lame', 'libopus'):
            rates['88.2 kHz'] = 88200
        if self.codec.library not in ('libmp3lame', 'libopus'):
            rates['96 kHz'] = 96000
        if self.codec.library not in ('aac', 'libfaac', 'libfdk_aac',
                                      'libmp3lame', 'libopus'):
            rates['192 kHz'] = 192000

        self.rate_label = Gtk.Label('Sample Rate')
        self.rate_label.set_halign(Gtk.Align.START)

        self.rate_cbtext = Gtk.ComboBoxText()
        self.rate_cbtext.set_property('hexpand', True)
        for r in rates:
            self.rate_cbtext.append_text(r)

        i = 0
        for r in rates:
            if rates[r] == self.codec.rate:
                self.rate_cbtext.set_active(i)
            else:
                i += 1

        self.rate_cbtext.connect('changed', self.on_rate_changed, rates)

    def resampler(self):
        resamplers = ['swr']
        if Soxr().is_avail():
            resamplers.append('soxr')

        self.resampler_label = Gtk.Label('Resampler')
        self.resampler_label.set_halign(Gtk.Align.START)

        self.resampler_cbtext = Gtk.ComboBoxText()
        self.resampler_cbtext.set_property('hexpand', True)
        for r in resamplers:
            self.resampler_cbtext.append_text(r)

        i = resamplers.index(self.codec.resampler)
        self.resampler_cbtext.set_active(i)

        self.resampler_cbtext.connect('changed', self.on_resampler_changed)

    def on_crf_changed(self, spin):
        self.codec.quality = spin.get_value_as_int()

    def on_preset_changed(self, cbtext):
        self.codec.preset = cbtext.get_active_text()

        # best libvpx preset implies cpu_used = 0
        if self.codec.library.startswith('libvpx'):
            if self.codec.preset == 'best':
                self.cpu_used_spin.set_sensitive(False)
            else:
                self.cpu_used_spin.set_sensitive(True)

    def on_tune_changed(self, cbtext):
        self.codec.tune = cbtext.get_active_text()

    def on_cpu_used_changed(self, spin):
        self.codec.cpu_used = spin.get_value_as_int()

    def on_arguments_changed(self, entry):
        self.codec.arguments = entry.get_text()

    def on_pixel_format_changed(self, cbtext, pixel_formats):
        self.codec.pixel_format = pixel_formats[cbtext.get_active_text()]

    def on_color_matrix_changed(self, cbtext, i, color_matrices):
        color_matrix = color_matrices[cbtext.get_active_text()]
        self.codec.color_matrix[i] = color_matrix

        # If one matrix is specified, the other must be different
        if i == 0:
            other_matrix_cbtext = self.output_matrix_cbtext
        elif i == 1:
            other_matrix_cbtext = self.input_matrix_cbtext
        other_matrix = color_matrices[other_matrix_cbtext.get_active_text()]

        if color_matrix == 'auto':
            other_matrix_cbtext.set_active(0)
        elif color_matrix == other_matrix or other_matrix == 'auto':
            k = 0
            for cm in color_matrices:
                if color_matrices[cm] not in ['auto', color_matrix]:
                    other_matrix_cbtext.set_active(k)
                else:
                    k += 1

    def on_mode_changed(self, cbtext):
        m = cbtext.get_active_text()
        if m == 'CBR' or m == 'ABR':
            self.bitrate_spin.set_sensitive(True)
            self.quality_spin.set_sensitive(False)
        elif m == 'VBR':
            self.bitrate_spin.set_sensitive(False)
            self.quality_spin.set_sensitive(True)
        self.codec.mode = m

    def on_bitrate_changed(self, spin):
        self.codec.mode = spin.get_value_as_int()

    def on_quality_changed(self, spin):
        self.codec.quality = spin.get_value_as_int()

    def on_channel_changed(self, cbtext, channels):
        self.codec.channel = channels[cbtext.get_active_text()]

    def on_rate_changed(self, cbtext, rates):
        self.codec.rate = rates[cbtext.get_active_text()]

    def on_resampler_changed(self, cbtext):
        self.codec.resampler = cbtext.get_active_text()


class VideoCodecDialog(CodecDialog):
    def __init__(self, codec, parent):
        CodecDialog.__init__(self, codec, parent)

        self.pixel_format()
        self.color_matrix()

        hsep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

        self.grid.attach(self.pixel_format_label, 0, 0, 1, 1)
        self.grid.attach(self.pixel_format_cbtext, 1, 0, 1, 1)
        self.grid.attach(self.input_matrix_label, 0, 1, 1, 1)
        self.grid.attach(self.input_matrix_cbtext, 1, 1, 1, 1)
        self.grid.attach(self.output_matrix_label, 0, 2, 1, 1)
        self.grid.attach(self.output_matrix_cbtext, 1, 2, 1, 1)
        self.grid.attach(hsep, 0, 3, 2, 1)


class VpxDialog(VideoCodecDialog):
    def __init__(self, codec, parent):
        VideoCodecDialog.__init__(self, codec, parent)

        crfs = Gtk.Adjustment(10, 0, 63, 1, 10)
        presets = ['best',
                   'good',
                   'realtime']
        cpus_used = Gtk.Adjustment(2, 0, 5, 1, 1)

        self.crf(crfs)
        self.preset(presets)
        self.cpu_used(cpus_used)
        self.arguments()

        self.grid.attach(self.crf_label, 0, 4, 1, 1)
        self.grid.attach_next_to(self.crf_spin, self.crf_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.preset_label, 0, 5, 1, 1)
        self.grid.attach_next_to(self.preset_cbtext, self.preset_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.cpu_used_label, 0, 6, 1, 1)
        self.grid.attach_next_to(self.cpu_used_spin, self.cpu_used_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.arguments_label, 0, 7, 2, 1)
        self.grid.attach(self.arguments_entry, 0, 8, 2, 1)

        self.show_all()


class Vp8Dialog(VpxDialog):
    def __init__(self, codec, parent):
        VpxDialog.__init__(self, codec, parent)


class Vp9Dialog(VpxDialog):
    def __init__(self, codec, parent):
        VpxDialog.__init__(self, codec, parent)


class X264Dialog(VideoCodecDialog):
    def __init__(self, codec, parent):
        VideoCodecDialog.__init__(self, codec, parent)

        crfs = Gtk.Adjustment(18, 1, 51, 1, 10)
        presets = ['none',
                   'ultrafast',
                   'superfast',
                   'veryfast',
                   'faster',
                   'fast',
                   'medium',
                   'slow',
                   'slower',
                   'veryslow',
                   'placebo']
        tunes = ['none',
                 'film',
                 'animation',
                 'grain',
                 'stillimage',
                 'psnr',
                 'ssim',
                 'fastdecode',
                 'zerolatency']

        self.crf(crfs)
        self.preset(presets)
        self.tune(tunes)
        self.arguments()

        self.grid.attach(self.crf_label, 0, 4, 1, 1)
        self.grid.attach_next_to(self.crf_spin, self.crf_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.preset_label, 0, 5, 1, 1)
        self.grid.attach_next_to(self.preset_cbtext, self.preset_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.tune_label, 0, 6, 1, 1)
        self.grid.attach_next_to(self.tune_cbtext, self.tune_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.arguments_label, 0, 7, 2, 1)
        self.grid.attach(self.arguments_entry, 0, 8, 2, 1)

        self.show_all()


class X265Dialog(VideoCodecDialog):
    def __init__(self, codec, parent):
        VideoCodecDialog.__init__(self, codec, parent)

        crfs = Gtk.Adjustment(18, 1, 51, 1, 10)
        presets = ['none',
                   'ultrafast',
                   'superfast',
                   'veryfast',
                   'faster',
                   'fast',
                   'medium',
                   'slow',
                   'slower',
                   'veryslow',
                   'placebo']

        self.crf(crfs)
        self.preset(presets)
        self.arguments()

        self.grid.attach(self.crf_label, 0, 4, 1, 1)
        self.grid.attach_next_to(self.crf_spin, self.crf_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.preset_label, 0, 5, 1, 1)
        self.grid.attach_next_to(self.preset_cbtext, self.preset_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.arguments_label, 0, 6, 2, 1)
        self.grid.attach(self.arguments_entry, 0, 7, 2, 1)

        self.show_all()


class AudioDialog(CodecDialog):
    def __init__(self, codec, parent):
        CodecDialog.__init__(self, codec, parent)

        self.channel()
        self.rate()
        self.resampler()

        hsep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

        self.grid.attach(self.channel_label, 0, 0, 1, 1)
        self.grid.attach(self.channel_cbtext, 1, 0, 1, 1)
        self.grid.attach(self.rate_label, 0, 1, 1, 1)
        self.grid.attach(self.rate_cbtext, 1, 1, 1, 1)
        self.grid.attach(self.resampler_label, 0, 2, 1, 1)
        self.grid.attach(self.resampler_cbtext, 1, 2, 1, 1)
        self.grid.attach(hsep, 0, 3, 2, 1)


class AacDialog(AudioDialog):
    def __init__(self, codec, parent):
        AudioDialog.__init__(self, codec, parent)

        modes = ['CBR']
        bitrates = Gtk.Adjustment(128, 0, 320, 1, 10)

        self.mode(modes)
        self.bitrate(bitrates)

        self.grid.attach(self.mode_label, 0, 4, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, self.mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.bitrate_label, 0, 5, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, self.bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

        self.show_all()


class FaacDialog(AudioDialog):
    def __init__(self, codec, parent):
        AudioDialog.__init__(self, codec, parent)

        modes = ['ABR', 'VBR']
        bitrates = Gtk.Adjustment(128, 0, 320, 1, 10)
        qualities = Gtk.Adjustment(100, 10, 500, 10, 100)

        self.mode(modes)
        self.bitrate(bitrates)
        self.quality(qualities)

        if self.codec.mode == 'VBR':
            self.bitrate_spin.set_sensitive(False)
        else:
            self.quality_spin.set_sensitive(False)

        self.grid.attach(self.mode_label, 0, 4, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, self.mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.bitrate_label, 0, 5, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, self.bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.quality_label, 0, 6, 1, 1)
        self.grid.attach_next_to(self.quality_spin, self.quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

        self.show_all()


class FdkaacDialog(AudioDialog):
    def __init__(self, codec, parent):
        AudioDialog.__init__(self, codec, parent)

        modes = ['CBR', 'VBR']
        bitrates = Gtk.Adjustment(128, 0, 320, 1, 10)
        qualities = Gtk.Adjustment(4, 1, 5, 1, 10)

        self.mode(modes)
        self.bitrate(bitrates)
        self.quality(qualities)

        if self.codec.mode == 'VBR':
            self.bitrate_spin.set_sensitive(False)
        else:
            self.quality_spin.set_sensitive(False)

        self.grid.attach(self.mode_label, 0, 4, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, self.mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.bitrate_label, 0, 5, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, self.bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.quality_label, 0, 6, 1, 1)
        self.grid.attach_next_to(self.quality_spin, self.quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

        self.show_all()


class FlacDialog(AudioDialog):
    def __init__(self, codec, parent):
        AudioDialog.__init__(self, codec, parent)

        self.show_all()


class LameDialog(AudioDialog):
    def __init__(self, codec, parent):
        AudioDialog.__init__(self, codec, parent)

        modes = ['CBR', 'ABR', 'VBR']
        bitrates = Gtk.Adjustment(320, 0, 320, 1, 10)
        qualities = Gtk.Adjustment(4, 0, 9, 1, 10)

        self.mode(modes)
        self.bitrate(bitrates)
        self.quality(qualities)

        if self.codec.mode == 'VBR':
            self.bitrate_spin.set_sensitive(False)
        else:
            self.quality_spin.set_sensitive(False)

        self.grid.attach(self.mode_label, 0, 4, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, self.mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.bitrate_label, 0, 5, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, self.bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.quality_label, 0, 6, 1, 1)
        self.grid.attach_next_to(self.quality_spin, self.quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

        self.show_all()


class OpusDialog(AudioDialog):
    def __init__(self, codec, parent):
        AudioDialog.__init__(self, codec, parent)

        modes = ['CBR', 'ABR', 'VBR']
        bitrates = Gtk.Adjustment(128, 6, 510, 1, 10)

        self.mode(modes)
        self.bitrate(bitrates)

        self.grid.attach(self.mode_label, 0, 4, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, self.mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.bitrate_label, 0, 5, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, self.bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

        self.show_all()


class VorbisDialog(AudioDialog):
    def __init__(self, codec, parent):
        AudioDialog.__init__(self, codec, parent)

        modes = ['CBR', 'ABR', 'VBR']
        bitrates = Gtk.Adjustment(160, 64, 500, 1, 10)
        qualities = Gtk.Adjustment(5, 0, 10, 1, 10)

        self.mode(modes)
        self.bitrate(bitrates)
        self.quality(qualities)

        if self.codec.mode == 'VBR':
            self.bitrate_spin.set_sensitive(False)
        else:
            self.quality_spin.set_sensitive(False)
            self.grid.attach(self.mode_label, 0, 4, 1, 1)

        self.grid.attach_next_to(self.mode_cbtext, self.mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.bitrate_label, 0, 5, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, self.bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.quality_label, 0, 6, 1, 1)
        self.grid.attach_next_to(self.quality_spin, self.quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

        self.show_all()

# vim: ts=4 sw=4 et:
