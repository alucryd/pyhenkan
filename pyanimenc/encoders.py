#!/usr/bin/env python3

import pyanimenc.conf as conf

from collections import OrderedDict

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk


class EncoderDialog(Gtk.Dialog):
    def __init__(self, parent, x):
        if x[0] == 'ffmpeg':
            n = x[1]
        else:
            n = x[0]

        Gtk.Dialog.__init__(self, n + ' settings', parent, 0, use_header_bar=1)
        self.set_default_size(240, 240)

        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(6)
        self.grid.set_row_spacing(6)
        self.grid.set_property('margin', 6)

        box = self.get_content_area()
        box.add(self.grid)

        if n.startswith('x264'):
            self._x264()
            self.connect('delete-event', self._update_x264)
        if n.startswith('x265'):
            self._x265()
            self.connect('delete-event', self._update_x265)
        if n == 'faac' or n == 'libfaac':
            self._hbar('aac')
            self._faac()
            self.connect('delete-event', self._update_faac)
        if n == 'fdkaac' or n == 'libfdk-aac':
            self._hbar('aac')
            self._fdkaac()
            self.connect('delete-event', self._update_fdkaac)
        if n == 'flac' or n == 'native-flac':
            self._hbar()
            self._flac()
            self.connect('delete-event', self._update_flac)
        if n == 'lame' or n == 'libmp3lame':
            self._hbar('mp3')
            self._mp3()
            self.connect('delete-event', self._update_mp3)
        if n == 'opusenc' or n == 'libopus':
            self._hbar('opus')
            self._opus()
            self.connect('delete-event', self._update_opus)
        if n == 'oggenc' or n == 'libvorbis':
            self._hbar()
            self._vorbis()
            self.connect('delete-event', self._update_vorbis)

        self.show_all()

    def _hbar(self, subset=''):
        icon = Gio.ThemedIcon(name='applications-system-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)

        grid = Gtk.Grid()
        grid.set_property('margin', 6)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)

        popover = Gtk.Popover()
        popover.set_modal(False)
        popover.add(grid)

        mbutton = Gtk.MenuButton()
        mbutton.set_image(image)
        mbutton.set_direction(Gtk.ArrowType.DOWN)
        mbutton.set_use_popover(True)
        mbutton.set_popover(popover)

        hbar = self.get_header_bar()
        hbar.pack_start(mbutton)

        self.channels = OrderedDict()
        self.channels['1.0'] = 1
        self.channels['2.0'] = 2
        if subset != 'mp3':
            self.channels['2.1'] = 3
        if subset != 'mp3':
            self.channels['4.0'] = 4
        if subset != 'mp3':
            self.channels['5.0'] = 5
        if subset != 'mp3':
            self.channels['5.1'] = 6
        if subset != 'mp3':
            self.channels['6.1'] = 7
        if subset != 'mp3':
            self.channels['7.1'] = 8

        self.rates = OrderedDict()
        self.rates['8 kHz'] = 8000
        if subset not in ('opus'):
            self.rates['11.025 kHz'] = 11025
        self.rates['16 kHz'] = 16000
        if subset not in ('opus'):
            self.rates['22.05 kHz'] = 22050
        self.rates['24 kHz'] = 24000
        if subset not in ('opus'):
            self.rates['32 kHz'] = 32000
        if subset not in ('opus'):
            self.rates['44.1 kHz'] = 44100
        self.rates['48 kHz'] = 48000
        if subset not in ('mp3', 'opus'):
            self.rates['64 kHz'] = 64000
        if subset not in ('mp3', 'opus'):
            self.rates['88.2 kHz'] = 88200
        if subset not in ('mp3', 'opus'):
            self.rates['96 kHz'] = 96000
        if subset not in ('aac', 'mp3', 'opus'):
            self.rates['192 kHz'] = 192000

        self.resamplers = ['swr']
        if conf.APROC:
            self.resamplers.append('soxr')

        channel_label = Gtk.Label('Channels')
        rate_label = Gtk.Label('Sample Rate')
        resampler_label = Gtk.Label('Resampler')

        self.channel_check = Gtk.CheckButton()
        self.channel_check.connect('toggled', self.on_channel_toggled)
        self.rate_check = Gtk.CheckButton()
        self.rate_check.connect('toggled', self.on_rate_toggled)

        self.channel_cbtext = Gtk.ComboBoxText()
        self.channel_cbtext.set_property('hexpand', True)
        for c in self.channels:
            self.channel_cbtext.append_text(c)
        self.channel_cbtext.set_sensitive(False)

        self.rate_cbtext = Gtk.ComboBoxText()
        self.rate_cbtext.set_property('hexpand', True)
        for r in self.rates:
            self.rate_cbtext.append_text(r)
        self.rate_cbtext.set_sensitive(False)

        self.resampler_cbtext = Gtk.ComboBoxText()
        self.resampler_cbtext.set_property('hexpand', True)
        for r in self.resamplers:
            self.resampler_cbtext.append_text(r)
        if len(self.resamplers) == 1:
            self.resampler_cbtext.set_sensitive(False)

        ch = conf.audio['channel']
        sr = conf.audio['rate']
        r = conf.audio['resampler']
        i = 0
        j = 0
        k = self.resamplers.index(r)
        for chk in self.channels:
            if not ch == self.channels[chk]:
                i += 1
            else:
                self.channel_check.set_active(True)
                self.channel_cbtext.set_active(i)
        for srk in self.rates:
            if not sr == self.rates[srk]:
                j += 1
            else:
                self.rate_check.set_active(True)
                self.rate_cbtext.set_active(j)
        self.resampler_cbtext.set_active(k)

        grid.attach(channel_label, 0, 0, 1, 1)
        grid.attach(self.channel_check, 1, 0, 1, 1)
        grid.attach(self.channel_cbtext, 2, 0, 1, 1)
        grid.attach(rate_label, 0, 1, 1, 1)
        grid.attach(self.rate_check, 1, 1, 1, 1)
        grid.attach(self.rate_cbtext, 2, 1, 1, 1)
        grid.attach(resampler_label, 0, 2, 2, 1)
        grid.attach(self.resampler_cbtext, 2, 2, 1, 1)

        grid.show_all()

    def _x264(self):
        quality = Gtk.Adjustment(18, 1, 51, 1, 10)
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
        conts = ['264',
                 'flv',
                 'mp4',
                 'mkv']

        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)
        preset_label = Gtk.Label('Preset')
        preset_label.set_halign(Gtk.Align.START)
        tune_label = Gtk.Label('Tune')
        tune_label.set_halign(Gtk.Align.START)
        cont_label = Gtk.Label('Container')
        cont_label.set_halign(Gtk.Align.START)
        arg_label = Gtk.Label('Custom arguments')
        arg_label.set_halign(Gtk.Align.CENTER)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(quality)

        self.preset_cbtext = Gtk.ComboBoxText()
        self.preset_cbtext.set_property('hexpand', True)
        for p in presets:
            self.preset_cbtext.append_text(p)

        self.tune_cbtext = Gtk.ComboBoxText()
        self.tune_cbtext.set_property('hexpand', True)
        for t in tunes:
            self.tune_cbtext.append_text(t)

        self.cont_cbtext = Gtk.ComboBoxText()
        self.cont_cbtext.set_property('hexpand', True)
        for c in conts:
            self.cont_cbtext.append_text(c)

        self.arg_entry = Gtk.Entry()
        self.arg_entry.set_property('hexpand', True)

        self.quality_spin.set_value(conf.x264['quality'])
        i = presets.index(conf.x264['preset'])
        self.preset_cbtext.set_active(i)
        j = tunes.index(conf.x264['tune'])
        self.tune_cbtext.set_active(j)
        k = conts.index(conf.x264['container'])
        self.cont_cbtext.set_active(k)
        self.arg_entry.set_text(conf.x264['arguments'])

        self.grid.attach(quality_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(preset_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.preset_cbtext, preset_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(tune_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.tune_cbtext, tune_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(cont_label, 0, 3, 1, 1)
        self.grid.attach_next_to(self.cont_cbtext, cont_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(arg_label, 0, 4, 2, 1)
        self.grid.attach(self.arg_entry, 0, 5, 2, 1)

    def _update_x264(self, widget, event):
        q = self.quality_spin.get_value_as_int()
        p = self.preset_cbtext.get_active_text()
        t = self.tune_cbtext.get_active_text()
        c = self.cont_cbtext.get_active_text()
        a = self.arg_entry.get_text()

        conf.x264['quality'] = q
        conf.x264['preset'] = p
        conf.x264['tune'] = t
        conf.x264['container'] = c
        conf.x264['arguments'] = a

    def _x265(self):
        quality = Gtk.Adjustment(18, 1, 51, 1, 10)
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
        conts = ['265']

        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)
        preset_label = Gtk.Label('Preset')
        preset_label.set_halign(Gtk.Align.START)
        tune_label = Gtk.Label('Tune')
        tune_label.set_halign(Gtk.Align.START)
        cont_label = Gtk.Label('Container')
        cont_label.set_halign(Gtk.Align.START)
        arg_label = Gtk.Label('Custom arguments')
        arg_label.set_halign(Gtk.Align.CENTER)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(quality)

        self.preset_cbtext = Gtk.ComboBoxText()
        self.preset_cbtext.set_property('hexpand', True)
        for p in presets:
            self.preset_cbtext.append_text(p)

        self.tune_cbtext = Gtk.ComboBoxText()
        self.tune_cbtext.set_property('hexpand', True)
        for t in tunes:
            self.tune_cbtext.append_text(t)

        self.cont_cbtext = Gtk.ComboBoxText()
        self.cont_cbtext.set_property('hexpand', True)
        for c in conts:
            self.cont_cbtext.append_text(c)

        self.arg_entry = Gtk.Entry()
        self.arg_entry.set_property('hexpand', True)

        self.quality_spin.set_value(conf.x265['quality'])
        i = presets.index(conf.x265['preset'])
        self.preset_cbtext.set_active(i)
        j = tunes.index(conf.x265['tune'])
        self.tune_cbtext.set_active(j)
        k = conts.index(conf.x265['container'])
        self.cont_cbtext.set_active(k)
        self.arg_entry.set_text(conf.x265['arguments'])

        self.grid.attach(quality_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(preset_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.preset_cbtext, preset_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(tune_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.tune_cbtext, tune_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(cont_label, 0, 3, 1, 1)
        self.grid.attach_next_to(self.cont_cbtext, cont_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(arg_label, 0, 4, 2, 1)
        self.grid.attach(self.arg_entry, 0, 5, 2, 1)

    def _update_x265(self, widget, event):
        q = self.quality_spin.get_value_as_int()
        p = self.preset_cbtext.get_active_text()
        t = self.tune_cbtext.get_active_text()
        c = self.cont_cbtext.get_active_text()
        a = self.arg_entry.get_text()

        conf.x265['quality'] = q
        conf.x265['preset'] = p
        conf.x265['tune'] = t
        conf.x265['container'] = c
        conf.x265['arguments'] = a

    def _faac(self):
        modes = ['ABR', 'VBR']
        bitrate = Gtk.Adjustment(128, 0, 320, 1, 10)
        quality = Gtk.Adjustment(100, 10, 500, 10, 100)
        conts = ['aac', 'm4a']

        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        bitrate_label = Gtk.Label('Bitrate')
        bitrate_label.set_halign(Gtk.Align.START)
        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)
        cont_label = Gtk.Label('Container')
        cont_label.set_halign(Gtk.Align.START)

        self.mode_cbtext = Gtk.ComboBoxText()
        self.mode_cbtext.set_property('hexpand', True)
        for m in modes:
            self.mode_cbtext.append_text(m)
        self.mode_cbtext.connect('changed', self.on_mode_changed)

        self.bitrate_spin = Gtk.SpinButton()
        self.bitrate_spin.set_property('hexpand', True)
        self.bitrate_spin.set_numeric(True)
        self.bitrate_spin.set_adjustment(bitrate)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(quality)

        self.cont_cbtext = Gtk.ComboBoxText()
        self.cont_cbtext.set_property('hexpand', True)
        for c in conts:
            self.cont_cbtext.append_text(c)

        i = modes.index(conf.faac['mode'])
        self.mode_cbtext.set_active(i)
        self.bitrate_spin.set_value(conf.faac['bitrate'])
        self.quality_spin.set_value(conf.faac['quality'])
        j = conts.index(conf.faac['container'])
        self.cont_cbtext.set_active(j)

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(bitrate_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(quality_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(cont_label, 0, 3, 1, 1)
        self.grid.attach_next_to(self.cont_cbtext, cont_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def _update_faac(self, widget, event):
        m = self.mode_cbtext.get_active_text()
        b = self.bitrate_spin.get_value_as_int()
        q = self.quality_spin.get_value_as_int()
        c = self.cont_cbtext.get_active_text()

        conf.faac['mode'] = m
        conf.faac['bitrate'] = b
        conf.faac['quality'] = q
        conf.faac['container'] = c

        self._update_audio()

    def _fdkaac(self):
        modes = ['CBR', 'VBR']
        bitrate = Gtk.Adjustment(128, 0, 320, 1, 10)
        quality = Gtk.Adjustment(4, 1, 5, 1, 10)
        conts = ['aac', 'm4a']

        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        bitrate_label = Gtk.Label('Bitrate')
        bitrate_label.set_halign(Gtk.Align.START)
        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)
        cont_label = Gtk.Label('Container')
        cont_label.set_halign(Gtk.Align.START)

        self.mode_cbtext = Gtk.ComboBoxText()
        self.mode_cbtext.set_property('hexpand', True)
        for m in modes:
            self.mode_cbtext.append_text(m)
        self.mode_cbtext.connect('changed', self.on_mode_changed)

        self.bitrate_spin = Gtk.SpinButton()
        self.bitrate_spin.set_property('hexpand', True)
        self.bitrate_spin.set_numeric(True)
        self.bitrate_spin.set_adjustment(bitrate)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(quality)

        self.cont_cbtext = Gtk.ComboBoxText()
        self.cont_cbtext.set_property('hexpand', True)
        for c in conts:
            self.cont_cbtext.append_text(c)

        i = modes.index(conf.fdkaac['mode'])
        self.mode_cbtext.set_active(i)
        self.bitrate_spin.set_value(conf.fdkaac['bitrate'])
        self.quality_spin.set_value(conf.fdkaac['quality'])
        j = conts.index(conf.fdkaac['container'])
        self.cont_cbtext.set_active(j)

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(bitrate_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(quality_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(cont_label, 0, 3, 1, 1)
        self.grid.attach_next_to(self.cont_cbtext, cont_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def _update_fdkaac(self, widget, event):
        m = self.mode_cbtext.get_active_text()
        b = self.bitrate_spin.get_value_as_int()
        q = self.quality_spin.get_value_as_int()
        c = self.cont_cbtext.get_active_text()

        conf.fdkaac['mode'] = m
        conf.fdkaac['bitrate'] = b
        conf.fdkaac['quality'] = q
        conf.fdkaac['container'] = c

        self._update_audio()

    def _flac(self):
        compression = Gtk.Adjustment(8, 0, 8, 1, 10)

        compression_label = Gtk.Label('Compression')
        compression_label.set_halign(Gtk.Align.START)

        self.compression_spin = Gtk.SpinButton()
        self.compression_spin.set_property('hexpand', True)
        self.compression_spin.set_numeric(True)
        self.compression_spin.set_adjustment(compression)

        self.compression_spin.set_value(conf.flac['compression'])

        self.grid.attach(compression_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.compression_spin, compression_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def _update_flac(self, widget, event):
        c = self.compression_spin.get_value_as_int()

        conf.flac['compression'] = c

        self._update_audio()

    def _mp3(self):
        modes = ['CBR', 'ABR', 'VBR']
        bitrate = Gtk.Adjustment(320, 0, 320, 1, 10)
        quality = Gtk.Adjustment(4, 0, 9, 1, 10)

        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        bitrate_label = Gtk.Label('Bitrate')
        bitrate_label.set_halign(Gtk.Align.START)
        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)

        self.mode_cbtext = Gtk.ComboBoxText()
        self.mode_cbtext.set_property('hexpand', True)
        for m in modes:
            self.mode_cbtext.append_text(m)
        self.mode_cbtext.connect('changed', self.on_mode_changed)

        self.bitrate_spin = Gtk.SpinButton()
        self.bitrate_spin.set_property('hexpand', True)
        self.bitrate_spin.set_numeric(True)
        self.bitrate_spin.set_adjustment(bitrate)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(quality)

        i = modes.index(conf.mp3['mode'])
        self.mode_cbtext.set_active(i)
        self.bitrate_spin.set_value(conf.mp3['bitrate'])
        self.quality_spin.set_value(conf.mp3['quality'])

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(bitrate_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(quality_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def _update_mp3(self, widget, event):
        m = self.mode_cbtext.get_active_text()
        b = self.bitrate_spin.get_value_as_int()
        q = self.quality_spin.get_value_as_int()

        conf.mp3['mode'] = m
        conf.mp3['bitrate'] = b
        conf.mp3['quality'] = q

        self._update_audio()

    def _opus(self):
        modes = ['CBR', 'ABR', 'VBR']
        bitrate = Gtk.Adjustment(128, 6, 510, 1, 10)

        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        bitrate_label = Gtk.Label('Bitrate')
        bitrate_label.set_halign(Gtk.Align.START)

        self.mode_cbtext = Gtk.ComboBoxText()
        self.mode_cbtext.set_property('hexpand', True)
        for m in modes:
            self.mode_cbtext.append_text(m)

        self.bitrate_spin = Gtk.SpinButton()
        self.bitrate_spin.set_property('hexpand', True)
        self.bitrate_spin.set_numeric(True)
        self.bitrate_spin.set_adjustment(bitrate)

        i = modes.index(conf.opus['mode'])
        self.mode_cbtext.set_active(i)
        self.bitrate_spin.set_value(conf.opus['bitrate'])

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(bitrate_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def _update_opus(self, widget, event):
        m = self.mode_cbtext.get_active_text()
        b = self.bitrate_spin.get_value_as_int()

        conf.opus['mode'] = m
        conf.opus['bitrate'] = b

        self._update_audio()

    def _vorbis(self):
        modes = ['CBR', 'ABR', 'VBR']
        bitrate = Gtk.Adjustment(160, 64, 500, 1, 10)
        quality = Gtk.Adjustment(5, 0, 10, 1, 10)

        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        bitrate_label = Gtk.Label('Bitrate')
        bitrate_label.set_halign(Gtk.Align.START)
        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)

        self.mode_cbtext = Gtk.ComboBoxText()
        self.mode_cbtext.set_property('hexpand', True)
        for m in modes:
            self.mode_cbtext.append_text(m)
        self.mode_cbtext.connect('changed', self.on_mode_changed)

        self.bitrate_spin = Gtk.SpinButton()
        self.bitrate_spin.set_property('hexpand', True)
        self.bitrate_spin.set_numeric(True)
        self.bitrate_spin.set_adjustment(bitrate)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(quality)

        i = modes.index(conf.vorbis['mode'])
        self.mode_cbtext.set_active(i)
        self.bitrate_spin.set_value(conf.vorbis['bitrate'])
        self.quality_spin.set_value(conf.vorbis['quality'])

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(bitrate_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(quality_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def _update_vorbis(self, widget, event):
        m = self.mode_cbtext.get_active_text()
        b = self.bitrate_spin.get_value_as_int()
        q = self.quality_spin.get_value_as_int()

        conf.vorbis['mode'] = m
        conf.vorbis['bitrate'] = b
        conf.vorbis['quality'] = q

        self._update_audio()

    def _update_audio(self):
        if self.channel_check.get_active():
            chk = self.channel_cbtext.get_active_text()
            ch = self.channels[chk]
        else:
            ch = 0
        if self.rate_check.get_active():
            srk = self.rate_cbtext.get_active_text()
            sr = self.rates[srk]
        else:
            sr = 0
        r = self.resampler_cbtext.get_active_text()

        conf.audio['channel'] = ch
        conf.audio['rate'] = sr
        conf.audio['resampler'] = r

    def on_mode_changed(self, combo):
        m = combo.get_active_text()
        if m == 'CBR' or m == 'ABR':
            self.bitrate_spin.set_sensitive(True)
            self.quality_spin.set_sensitive(False)
        elif m == 'VBR':
            self.bitrate_spin.set_sensitive(False)
            self.quality_spin.set_sensitive(True)

    def on_rate_toggled(self, check):
        s = self.rate_check.get_active()
        self.rate_cbtext.set_sensitive(s)

    def on_channel_toggled(self, check):
        s = self.channel_check.get_active()
        self.channel_cbtext.set_sensitive(s)
