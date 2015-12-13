#!/usr/bin/env python3

import os
import subprocess
import tempfile
from collections import OrderedDict

import pyhenkan.conf as conf
from pyhenkan.mediafile import MediaFile
from pyhenkan.transcode import Transcode
from pyhenkan.vapoursynth import VapourSynthDialog, VapourSynthScript

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk


class ScriptCreatorWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='pyanimscript')
        self.set_default_size(640, 520)

        # Set default working directory
        self.wdir = os.environ['HOME']
        self.source = None

        # --Header Bar-- #
        open_button = Gtk.Button('Open')
        open_button.connect('clicked', self.on_open_clicked)

        self.save_button = Gtk.Button('Save')
        self.save_button.set_sensitive(False)
        self.save_button.connect('clicked', self.on_save_clicked)

        self.preview_button = Gtk.Button('Preview')
        self.preview_button.set_sensitive(False)
        self.preview_button.connect('clicked', self.on_preview_clicked)

        settings_icon = Gio.ThemedIcon(name='applications-system-symbolic')
        settings_image = Gtk.Image.new_from_gicon(settings_icon,
                                                  Gtk.IconSize.BUTTON)
        settings_button = Gtk.Button()
        settings_button.set_image(settings_image)
        settings_button.connect('clicked', self.on_settings_clicked)

        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.pack_start(open_button)
        hbar.pack_start(self.save_button)
        hbar.pack_start(self.preview_button)
        hbar.pack_end(settings_button)

        self.set_titlebar(hbar)

        # --Open/Save--#
        self.open_fcdlg = Gtk.FileChooserDialog('Open Video File', self,
                                                Gtk.FileChooserAction.OPEN,
                                                ('Cancel',
                                                 Gtk.ResponseType.CANCEL,
                                                 'Open', Gtk.ResponseType.OK))
        self.open_fcdlg.set_current_folder(self.wdir)
        self.open_fcdlg.add_filter(conf.vflt)

        self.save_fcdlg = Gtk.FileChooserDialog('Save VapourSynth Script',
                                                self,
                                                Gtk.FileChooserAction.SAVE,
                                                ('Cancel',
                                                 Gtk.ResponseType.CANCEL,
                                                 'Save', Gtk.ResponseType.OK))
        self.save_fcdlg.set_current_folder(self.wdir)
        self.save_fcdlg.add_filter(conf.sflt)

        # --Textview--#
        self.tbuffer = Gtk.TextBuffer()

        tview = Gtk.TextView()
        tview.set_buffer(self.tbuffer)
        tview.set_left_margin(6)
        tview.set_right_margin(6)

        self.add(tview)

    def _update_buffer(self):
        s = VapourSynthScript().script(self.source.path, conf.filters)
        self.tbuffer.set_text(s)

    def on_open_clicked(self, button):
        response = self.open_fcdlg.run()

        if response == Gtk.ResponseType.OK:
            if self.source:
                self.preview_win.destroy()

            f = self.open_fcdlg.get_filename()
            self.source = MediaFile(f)

            self._update_buffer()
            self.save_button.set_sensitive(True)
            self.preview_button.set_sensitive(True)

            self.preview_win = PreviewWindow(self.source)

        self.open_fcdlg.hide()

    def on_save_clicked(self, button):
        o = '.'.join([self.source.bname,  'vpy'])
        o = '/'.join([self.source.dname, o])

        self.save_fcdlg.set_filename(o)

        response = self.save_fcdlg.run()

        if response == Gtk.ResponseType.OK:
            o = self.save_fcdlg.get_filename()
            if not o.endswith('.vpy'):
                o += '.vpy'

            s = self.tbuffer.get_text(self.tbuffer.get_start_iter(),
                                      self.tbuffer.get_end_iter(),
                                      include_hidden_chars=True)

            with open(o, 'w') as f:
                f.write(s)

        self.save_fcdlg.hide()

    def on_preview_clicked(self, button):
        self.preview_win.refresh()
        self.preview_win.show_all()

    def on_settings_clicked(self, button):
        dlg = VapourSynthDialog(self)
        dlg.run()
        if self.source:
            self._update_buffer()
        dlg.destroy()


class PreviewWindow(Gtk.Window):
    def __init__(self, source):
        Gtk.Window.__init__(self, title='Preview')

        self.source = source
        self.trans = Transcode(self.source.tracklist[0], None)

        self.tempdir = tempfile.gettempdir()
        basename = '/'.join([self.tempdir, 'pyhenkan-preview'])
        self.png = basename + '%d.png'
        self.vpy = basename + '.vpy'

        self.trans.script(self.vpy, conf.filters)
        d = self.trans.info()
        self.frame = round((d - 1) / 2)

        self.image = Gtk.Image()

        scrwin = Gtk.ScrolledWindow()
        scrwin.set_min_content_width(848)
        scrwin.set_min_content_height(480)
        scrwin.add(self.image)

        adj = Gtk.Adjustment(self.frame, 0, d - 1, 1, 10)

        self.spin = Gtk.SpinButton()
        self.spin.set_adjustment(adj)
        self.spin.set_numeric(True)
        self.spin.connect('value-changed', self.on_spin_changed)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,
                                              0, d - 1, 1)
        self.scale.set_property('hexpand', True)
        self.scale.set_property('halign', Gtk.Align.FILL)
        self.scale.set_draw_value(False)
        self.scale.set_value(self.frame)
        self.scale.connect('value-changed', self.on_scale_changed)

        for i in range(0, d, 500):
            self.scale.add_mark(i, Gtk.PositionType.TOP, str(i))

        refresh_button = Gtk.Button('Refresh')
        refresh_button.connect('clicked', self.on_refresh_clicked)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_spacing(6)
        hbox.set_property('margin', 6)
        hbox.pack_start(self.spin, False, True, 0)
        hbox.pack_start(self.scale, True, True, 0)
        hbox.pack_start(refresh_button, False, True, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(scrwin, True, True, 0)
        vbox.pack_start(hbox, False, True, 0)

        self.add(vbox)

    def on_scale_changed(self, scale):
        value = int(scale.get_value())
        if self.spin.get_value != value:
            self.spin.set_value(value)
            self.frame = value
            self.refresh()

    def on_spin_changed(self, spin):
        value = spin.get_value()
        if int(self.scale.get_value()) != value:
            self.scale.set_value(value)
            self.frame = value
            self.refresh()

    def on_refresh_clicked(self, button):
        self.refresh()

    def refresh(self):
        args_trim = OrderedDict()
        args_trim['first'] = self.frame
        args_trim['last'] = self.frame
        args_res = OrderedDict()
        args_res['format'] = 'vs.RGB24'
        args_imwri = OrderedDict()
        args_imwri['imgformat'] = '"PNG"'
        args_imwri['filename'] = '"' + self.png + '"'
        flts = conf.filters + [['Resize', 'Bilinear', args_res],
                               ['Misc', 'Trim', args_trim],
                               ['ImageMagick', 'Write', args_imwri]]

        self.trans.script(self.vpy, flts)
        self.trans.preview()

        self.image.set_from_file(self.png.replace('%d', str(0)))

# vim: ts=4 sw=4 et:
