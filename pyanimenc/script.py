#!/usr/bin/env python3

import os

import pyanimenc.conf as conf
from pyanimenc.vapoursynth import VapourSynthDialog, VapourSynthScript

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk

class ScriptCreatorWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='pyanimscript')
        self.set_default_size(640, 520)

        self.source = ''

        # --Header Bar--#
        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.set_property('title', 'pyanimscript')

        open_button = Gtk.Button('Open')
        open_button.connect('clicked', self.on_open_clicked)
        save_button = Gtk.Button('Save')
        save_button.connect('clicked', self.on_save_clicked)

        settings_button = Gtk.Button()
        settings_icon = Gio.ThemedIcon(name='applications-system-symbolic')
        settings_image = Gtk.Image.new_from_gicon(settings_icon,
                                                  Gtk.IconSize.BUTTON)
        settings_button.set_image(settings_image)
        settings_button.connect('clicked', self.on_settings_clicked)

        hbar.pack_start(open_button)
        hbar.pack_start(save_button)
        hbar.pack_end(settings_button)

        self.set_titlebar(hbar)

        # --Open/Save--#
        self.open_fcdlg = Gtk.FileChooserDialog('Open Video File', self,
                                                Gtk.FileChooserAction.OPEN,
                                                ('Cancel',
                                                 Gtk.ResponseType.CANCEL,
                                                 'Open', Gtk.ResponseType.OK))
        self.open_fcdlg.add_filter(conf.vflt)
        self.save_fcdlg = Gtk.FileChooserDialog('Save VapourSynth Script',
                                                self,
                                                Gtk.FileChooserAction.SAVE,
                                                ('Cancel',
                                                 Gtk.ResponseType.CANCEL,
                                                 'Save', Gtk.ResponseType.OK))
        self.save_fcdlg.add_filter(conf.sflt)

        # --Textview--#
        self.tbuffer = Gtk.TextBuffer()
        tview = Gtk.TextView()
        tview.set_buffer(self.tbuffer)
        tview.set_left_margin(6)
        tview.set_right_margin(6)

        self.add(tview)

    def _update_buffer(self):
        s = VapourSynthScript().script(self.source, conf.filters)
        self.tbuffer.set_text(s)

    def on_open_clicked(self, button):
        response = self.open_fcdlg.run()

        if response == Gtk.ResponseType.OK:
            self.source = self.open_fcdlg.get_filename()

            self._update_buffer()

        self.open_fcdlg.hide()

    def on_save_clicked(self, button):
        o = os.path.splitext(self.source)[0] + '.vpy'
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

    def on_settings_clicked(self, button):
        dlg = VapourSynthDialog(self)
        dlg.run()
        if self.source:
            self._update_buffer()
        dlg.destroy()

# vim: ts=4 sw=4 et:
