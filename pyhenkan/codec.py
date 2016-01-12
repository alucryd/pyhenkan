import io
import os
import subprocess

from collections import OrderedDict
from decimal import Decimal

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class Codec:
    def __init__(self, binary, library):
        self.binary = binary
        self.library = library

    def is_avail(self):
        path = os.environ['PATH'].split(':')
        for p in path:
            if os.path.isfile('/'.join([p, self.binary])):
                return True
        return False

    def show_dialog(self, dlg):
        dlg.run()
        dlg.destroy()


class X264(Codec):
    def __init__(self, binary, depth):
        Codec.__init__(self, binary, '')
        self.depth = depth
        self.quality = 18
        self.preset = 'medium'
        self.tune = 'none'
        self.container = '264'
        self.arguments = ''

    def is_avail(self):
        if super().is_avail():
            proc = subprocess.run([self.binary, '--version'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL,
                                  universal_newlines=True)
            buf = io.StringIO(proc.stdout)
            line = buf.readline()
            while line:
                if '='.join(['bit-depth', str(self.depth)]) in line:
                    return True
                line = buf.readline()
        return False

    def show_dialog(self, parent):
        dlg = X264Dialog(self, parent)
        super().show_dialog(dlg)

    def command(self, input, output):
        dec = 'vspipe "{}" - -y'.format(input)
        enc = [self.binary,
               '--crf', str(self.quality),
               '--demuxer', 'y4m']
        if self.preset != 'none':
            enc += ['--preset', self.preset]
        if self.tune != 'none':
            enc += ['--tune', self.tune]
        if self.arguments:
            enc.append(self.arguments)
        enc += ['--output', '"{}.{}" -'.format(output, self.container)]
        enc = ' '.join(enc)
        cmd = ' | '.join([dec, enc])
        return cmd


class X265(Codec):
    def __init__(self, binary, depth):
        Codec.__init__(self, binary, '')
        self.depth = depth
        self.quality = 18
        self.preset = 'medium'
        self.tune = 'none'
        self.container = '265'
        self.arguments = ''

    def is_avail(self):
        if super().is_avail():
            proc = subprocess.run([self.binary, '--version',
                                   '--output-depth', str(self.depth)],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE,
                                  universal_newlines=True)
            buf = io.StringIO(proc.stderr)
            tokens = [str(self.depth) + s for s in ['bit', 'bpp']]
            line = buf.readline()
            while line:
                if tokens[0] in line or tokens[1] in line:
                    return True
                line = buf.readline()
        return False

    def show_dialog(self, parent):
        dlg = X265Dialog(self, parent)
        super().show_dialog(dlg)

    def command(self, input, output):
        dec = 'vspipe "{}" - -y'.format(input)
        enc = [self.binary,
               '--output-depth', str(self.depth),
               '--crf', str(self.quality),
               '--y4m']
        if self.preset != 'none':
            enc += ['--preset', self.preset]
        if self.tune != 'none':
            enc += ['--tune', self.tune]
        if self.arguments:
            enc.append(self.arguments)
        enc += ['--output', '"{}.{}" -'.format(output, self.container)]
        enc = ' '.join(enc)
        cmd = ' | '.join([dec, enc])
        return cmd


class AudioCodec(Codec):
    def __init__(self, binary, library):
        Codec.__init__(self, binary, library)
        self.channel = 0
        self.rate = 0
        self.resampler = 'swr'

    def is_avail(self):
        if super().is_avail():
            proc = subprocess.run([self.binary, '-buildconf'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL,
                                  universal_newlines=True)
            buf = io.StringIO(proc.stdout)
            token = '-'.join(['enable', self.library])
            line = buf.readline()
            while line:
                if token in line or self.library == 'flac':
                    return True
                line = buf.readline()
        return False

    def command(self, track):
        dec = 'ffmpeg -y -i "{}" -map 0:{} -c {}'
        cmd = [dec.format(track.file.path, track.id,
                          self.library.replace('-', '_'))]
        if self.channel != track.channel:
            cmd.append('-ac {}'.format(self.channel))
        if self.rate != track.rate:
            cmd.append('-ar {}'.format(self.rate))
        if self.resampler != 'swr':
            cmd.append('-af aresample=resampler={}'.format(self.resampler))
        t = [track.file.first, track.file.last]
        n = track.file.fpsnum
        d = track.file.fpsden
        if t != [0, 0] and [n, d] != [0, 1]:
            f = Decimal(t[0]) * Decimal(d) / Decimal(n)
            l = Decimal(t[1] + 1) * Decimal(d) / Decimal(n)
            cmd.append('-af atrim={}:{}'.format(f, l))
        return cmd


class Faac(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'ffmpeg', 'libfaac')
        self.mode = 'VBR'
        self.bitrate = 128
        self.quality = 100
        self.container = 'aac'

    def show_dialog(self, parent):
        dlg = FaacDialog(self, parent)
        super().show_dialog(dlg)

    def command(self, track, output):
        cmd = super().command(track)
        if self.mode == 'ABR':
            cmd.append('-b {}'.format(self.bitrate))
        elif self.mode == 'VBR':
            cmd.append('-q {}'.format(self.quality))
        cmd.append('"{}.{}"'.format(output, self.container))
        cmd = ' '.join(cmd)
        return cmd


class Fdkaac(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'ffmpeg', 'libfdk-aac')
        self.mode = 'VBR'
        self.bitrate = 128
        self.quality = 4
        self.container = 'aac'

    def show_dialog(self, parent):
        dlg = FdkaacDialog(self, parent)
        super().show_dialog(dlg)

    def command(self, track, output):
        cmd = super().command(track)
        if self.mode == 'CBR':
            cmd.append('-b {}'.format(self.bitrate))
        elif self.mode == 'VBR':
            cmd.append('-vbr {}'.format(self.quality))
        cmd.append('"{}.{}"'.format(output, self.container))
        cmd = ' '.join(cmd)
        return cmd


class Flac(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'ffmpeg', 'flac')
        self.compression = 8
        self.container = 'flac'

    def show_dialog(self, parent):
        dlg = FlacDialog(self, parent)
        super().show_dialog(dlg)

    def command(self, track, output):
        cmd = super().command(track)
        cmd.append('-compression_level {}'.format(self.compression))
        cmd.append('"{}.{}"'.format(output, self.container))
        cmd = ' '.join(cmd)
        return cmd


class Lame(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'ffmpeg', 'libmp3lame')
        self.mode = 'VBR'
        self.bitrate = 192
        self.quality = 2
        self.container = 'mp3'

    def show_dialog(self, parent):
        dlg = LameDialog(self, parent)
        super().show_dialog(dlg)

    def command(self, track, output):
        cmd = super().command(track)
        if self.mode == 'CBR':
            cmd.append('-b {}'.format(self.bitrate))
        elif self.mode == 'ABR':
            cmd.append('-b {} -abr'.format(self.bitrate))
        elif self.mode == 'VBR':
            cmd.append('-compression_level {}'.format(self.quality))
        cmd.append('"{}.{}"'.format(output, self.container))
        cmd = ' '.join(cmd)
        return cmd


class Opus(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'ffmpeg', 'libopus')
        self.mode = 'VBR'
        self.bitrate = 128
        self.container = 'opus'

    def show_dialog(self, parent):
        dlg = OpusDialog(self, parent)
        super().show_dialog(dlg)

    def command(self, track, output):
        cmd = super().command(track)
        cmd.append('-b {}'.format(self.bitrate * 1000))
        if self.mode == 'CBR':
            cmd.append('-vbr off')
        elif self.mode == 'ABR':
            cmd.append('-vbr constrained')
        cmd.append('"{}.{}"'.format(output, self.container))
        cmd = ' '.join(cmd)
        return cmd


class Vorbis(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'ffmpeg', 'libvorbis')
        self.mode = 'VBR'
        self.bitrate = 160
        self.quality = 5
        self.container = 'ogg'

    def show_dialog(self, parent):
        dlg = VorbisDialog(self, parent)
        super().show_dialog(dlg)

    def command(self, track, output):
        cmd = super().command(track)
        if self.mode == 'CBR':
            cmd.append('-b {} -m {} -M {}'.format(self.bitrate, self.bitrate,
                                                  self.bitrate))
        elif self.mode == 'ABR':
            cmd.append('-b {}'.format(self.bitrate))
        elif self.mode == 'VBR':
            cmd.append('-q {}'.format(self.quality))
        cmd.append('"{}.{}"'.format(output, self.container))
        cmd = ' '.join(cmd)
        return cmd


class Dcadec(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'ffmpeg', 'libdcadec')


class Soxr(AudioCodec):
    def __init__(self):
        AudioCodec.__init__(self, 'ffmpeg', 'libsoxr')


class CodecDialog(Gtk.Dialog):
    def __init__(self, codec, parent):
        title = codec.library if codec.library else codec.binary
        Gtk.Dialog.__init__(self, title, parent, Gtk.DialogFlags.MODAL)
        self.set_default_size(240, 0)

        self.codec = codec

        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(6)
        self.grid.set_row_spacing(6)
        self.grid.set_property('margin', 6)

        box = self.get_content_area()
        box.add(self.grid)

    def quality(self, qualities):
        self.quality_label = Gtk.Label('Quality')
        self.quality_label.set_halign(Gtk.Align.START)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(qualities)
        self.quality_spin.set_value(self.codec.quality)
        self.quality_spin.connect('value-changed', self.on_quality_changed)

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

    def container(self, containers):
        self.container_label = Gtk.Label('Container')
        self.container_label.set_halign(Gtk.Align.START)

        self.container_cbtext = Gtk.ComboBoxText()
        self.container_cbtext.set_property('hexpand', True)
        for c in containers:
            self.container_cbtext.append_text(c)
        i = containers.index(self.codec.container)
        self.container_cbtext.set_active(i)
        self.container_cbtext.connect('changed', self.on_container_changed)

    def arguments(self):
        self.arguments_label = Gtk.Label('Custom arguments')
        self.arguments_label.set_halign(Gtk.Align.CENTER)

        self.arguments_entry = Gtk.Entry()
        self.arguments_entry.set_property('hexpand', True)
        self.arguments_entry.set_text(self.codec.arguments)
        self.arguments_entry.connect('changed', self.on_arguments_changed)

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

    def compression(self, compressions):
        self.compression_label = Gtk.Label('Compression')
        self.compression_label.set_halign(Gtk.Align.START)

        self.compression_spin = Gtk.SpinButton()
        self.compression_spin.set_property('hexpand', True)
        self.compression_spin.set_numeric(True)
        self.compression_spin.set_adjustment(compressions)
        self.compression_spin.set_value(self.codec.compression)
        self.compression_spin.connect('value-changed',
                                      self.on_compression_changed)

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
            if not self.codec.channel == channels[c]:
                i += 1
            else:
                self.channel_cbtext.set_active(i)

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
        if self.codec.library not in ('libmp3lame', 'liboups'):
            rates['64 kHz'] = 64000
        if self.codec.library not in ('libmp3lame', 'libopus'):
            rates['88.2 kHz'] = 88200
        if self.codec.library not in ('libmp3lame', 'libopus'):
            rates['96 kHz'] = 96000
        if self.codec.library not in ('libfaac', 'libfdk-aac', 'libmp3lame',
                                      'libopus'):
            rates['192 kHz'] = 192000

        self.rate_label = Gtk.Label('Sample Rate')
        self.rate_label.set_halign(Gtk.Align.START)

        self.rate_cbtext = Gtk.ComboBoxText()
        self.rate_cbtext.set_property('hexpand', True)
        for r in rates:
            self.rate_cbtext.append_text(r)

        i = 0
        for r in rates:
            if not self.codec.rate == rates[r]:
                i += 1
            else:
                self.rate_cbtext.set_active(i)

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

    def on_quality_changed(self, spin):
        self.codec.quality = spin.get_value_as_int()

    def on_preset_changed(self, cbtext):
        self.codec.preset = cbtext.get_active_text()

    def on_tune_changed(self, cbtext):
        self.codec.tune = cbtext.get_active_text()

    def on_container_changed(self, cbtext):
        self.codec.container = cbtext.get_active_text()

    def on_arguments_changed(self, entry):
        self.codec.arguments = entry.get_text()

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

    def on_compression_changed(self, spin):
        self.codec.compression = spin.get_value_as_int()

    def on_channel_changed(self, cbtext, channels):
        self.codec.channel = channels[cbtext.get_active_text()]

    def on_rate_changed(self, cbtext, rates):
        self.codec.rate = rates[cbtext.get_active_text()]

    def on_resampler_changed(self, cbtext):
        self.codec.resampler = cbtext.get_active_text()


class X264Dialog(CodecDialog):
    def __init__(self, codec, parent):
        CodecDialog.__init__(self, codec, parent)

        qualities = Gtk.Adjustment(18, 1, 51, 1, 10)
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
        containers = ['264',
                      'flv',
                      'mp4',
                      'mkv']

        self.quality(qualities)
        self.preset(presets)
        self.tune(tunes)
        self.container(containers)
        self.arguments()

        self.grid.attach(self.quality_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.quality_spin, self.quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.preset_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.preset_cbtext, self.preset_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.tune_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.tune_cbtext, self.tune_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.container_label, 0, 3, 1, 1)
        self.grid.attach_next_to(self.container_cbtext, self.container_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.arguments_label, 0, 4, 2, 1)
        self.grid.attach(self.arguments_entry, 0, 5, 2, 1)

        self.show_all()


class X265Dialog(CodecDialog):
    def __init__(self, codec, parent):
        CodecDialog.__init__(self, codec, parent)

        qualities = Gtk.Adjustment(18, 1, 51, 1, 10)
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
                 'psnr',
                 'ssim',
                 'fastdecode',
                 'zerolatency']
        containers = ['265']

        self.quality(qualities)
        self.preset(presets)
        self.tune(tunes)
        self.container(containers)
        self.arguments()

        self.grid.attach(self.quality_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.quality_spin, self.quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.preset_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.preset_cbtext, self.preset_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.tune_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.tune_cbtext, self.tune_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.container_label, 0, 3, 1, 1)
        self.grid.attach_next_to(self.container_cbtext, self.container_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(self.arguments_label, 0, 4, 2, 1)
        self.grid.attach(self.arguments_entry, 0, 5, 2, 1)

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


class FaacDialog(AudioDialog):
    def __init__(self, codec, parent):
        AudioDialog.__init__(self, codec, parent)

        modes = ['ABR', 'VBR']
        bitrates = Gtk.Adjustment(128, 0, 320, 1, 10)
        qualities = Gtk.Adjustment(100, 10, 500, 10, 100)
        containers = ['aac', 'm4a']

        self.mode(modes)
        self.bitrate(bitrates)
        self.quality(qualities)
        self.containers(containers)

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
        self.grid.attach(self.container_label, 0, 7, 1, 1)
        self.grid.attach_next_to(self.container_cbtext, self.container_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

        self.show_all()


class FdkaacDialog(AudioDialog):
    def __init__(self, codec, parent):
        AudioDialog.__init__(self, codec, parent)

        modes = ['CBR', 'VBR']
        bitrates = Gtk.Adjustment(128, 0, 320, 1, 10)
        qualities = Gtk.Adjustment(4, 1, 5, 1, 10)
        containers = ['aac', 'm4a']

        self.mode(modes)
        self.bitrate(bitrates)
        self.quality(qualities)
        self.container(containers)

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
        self.grid.attach(self.container_label, 0, 7, 1, 1)
        self.grid.attach_next_to(self.container_cbtext, self.container_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

        self.show_all()


class FlacDialog(AudioDialog):
    def __init__(self, codec, parent):
        AudioDialog.__init__(self, codec, parent)

        compressions = Gtk.Adjustment(8, 0, 8, 1, 10)

        self.compression(compressions)

        self.grid.attach(self.compression_label, 0, 4, 1, 1)
        self.grid.attach_next_to(self.compression_spin, self.compression_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

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
