#!/usr/bin/env python3

import copy
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pyanimenc.command as command
import pyanimenc.conf as conf
from pyanimenc.chapter import ChapterEditorWindow
from pyanimenc.encoders import EncoderDialog
from pyanimenc.mediainfo import Parse
from pyanimenc.script import ScriptCreatorWindow
from pyanimenc.vapoursynth import VapourSynthDialog, VapourSynthScript

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import Gio, GLib, GObject, Gtk, Notify

VERSION = '0.1.0'
AUTHOR = 'Maxime Gauduin <alucryd@gmail.com>'


class MainWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='pyanimenc')
        self.set_default_size(800, 600)

        self.connect('delete-event', self.on_delete_event)

        # Set default working directory
        self.wdir = os.environ['HOME']

        # Initialize a lock and acquire it
        # Any subsequent acquire() will block the calling thread
        self.lock = Lock()
        self.lock.acquire()
        # Mark as idle, this will be useful later
        self.idle = True
        self.waitlist = []
        # Set up single worker thread and lock it
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.worker.submit(self._wait)

        # Notification
        Notify.init('pyanimenc')
        self.notification = Notify.Notification.new('pyanimenc',
                                                    '',
                                                    'dialog-information')
        self.notification.set_urgency(1)

        # --Header Bar-- #
        tools_sccr_button = Gtk.Button()
        tools_sccr_button.set_label('Script Creator')
        tools_sccr_button.connect('clicked', self.on_sccr_clicked)

        tools_ched_button = Gtk.Button()
        tools_ched_button.set_label('Chapter Editor')
        tools_ched_button.connect('clicked', self.on_ched_clicked)

        tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        tools_box.set_property('margin', 6)
        tools_box.pack_start(tools_sccr_button, True, True, 0)
        tools_box.pack_start(tools_ched_button, True, True, 0)
        tools_box.show_all()

        tools_popover = Gtk.Popover()
        tools_popover.add(tools_box)

        open_button = Gtk.Button('Open')
        open_button.set_property('hexpand', True)
        open_button.connect('clicked', self.on_open_clicked)

        tools_mbutton = Gtk.MenuButton()
        tools_mbutton.set_label('Tools')
        tools_mbutton.set_direction(Gtk.ArrowType.DOWN)
        tools_mbutton.set_use_popover(True)
        tools_mbutton.set_popover(tools_popover)

        about_button = Gtk.Button()
        about_button.set_label('About')
        about_button.connect('clicked', self.on_about_clicked)

        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.set_property('title', 'pyanimenc')
        hbar.pack_start(open_button)
        hbar.pack_start(tools_mbutton)
        hbar.pack_end(about_button)

        self.set_titlebar(hbar)

        # --Input-- #
        vid_label = Gtk.Label('Video Codec')
        vid_label.set_property('hexpand', True)

        aud_label = Gtk.Label('Audio Codec')
        aud_label.set_property('hexpand', True)

        fname_label = Gtk.Label('Filename')
        fname_label.set_property('hexpand', True)
        suffix_label = Gtk.Label('Suffix')
        suffix_label.set_property('hexpand', True)
        cont_label = Gtk.Label('Container')
        cont_label.set_property('hexpand', True)
        cont_label.set_property('margin_left', 6)
        cont_label.set_property('margin_right', 6)
        out_uscore_label = Gtk.Label('_')
        out_dot_label = Gtk.Label('.')

        self.out_name_entry = Gtk.Entry()
        self.out_name_entry.set_sensitive(False)
        self.out_name_entry.set_property('hexpand', True)

        self.out_suffix_entry = Gtk.Entry()
        self.out_suffix_entry.set_text('new')
        self.out_suffix_entry.set_property('hexpand', True)

        self.out_cont_cbtext = Gtk.ComboBoxText()
        self.out_cont_cbtext.set_property('hexpand', True)
        for cont in conf.VCONTS:
            self.out_cont_cbtext.append_text(cont)
        self.out_cont_cbtext.set_active(0)

        out_grid = Gtk.Grid()
        out_grid.set_row_homogeneous(True)
        out_grid.set_column_spacing(6)
        out_grid.set_row_spacing(6)
        out_grid.attach(fname_label, 0, 0, 1, 1)
        out_grid.attach(self.out_name_entry, 0, 1, 1, 1)
        out_grid.attach(out_uscore_label, 1, 1, 1, 1)
        out_grid.attach(suffix_label, 2, 0, 1, 1)
        out_grid.attach(self.out_suffix_entry, 2, 1, 1, 1)
        out_grid.attach(out_dot_label, 3, 1, 1, 1)
        out_grid.attach(cont_label, 4, 0, 1, 1)
        out_grid.attach(self.out_cont_cbtext, 4, 1, 1, 1)

        hsep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

        self.venc_cbtext = Gtk.ComboBoxText()
        self.venc_cbtext.set_property('hexpand', True)
        for x in conf.VENCS:
            self.venc_cbtext.append_text(x)
            self.venc_cbtext.set_active(0)

        self.aenc_cbtext = Gtk.ComboBoxText()
        self.aenc_cbtext.set_property('hexpand', True)
        for x in conf.AENCS:
            self.aenc_cbtext.append_text(x)
            self.aenc_cbtext.set_active(0)

        conf_icon = Gio.ThemedIcon(name='applications-system-symbolic')
        # queue_icon = Gio.ThemedIcon(name='list-add-symbolic')

        vpyconf_button = Gtk.Button('VapourSynth filters')
        vpyconf_button.connect('clicked', self.on_conf_clicked, 'input')

        vconf_image = Gtk.Image.new_from_gicon(conf_icon, Gtk.IconSize.BUTTON)
        vconf_button = Gtk.Button()
        vconf_button.set_image(vconf_image)
        vconf_button.connect('clicked', self.on_conf_clicked, 'video')

        aconf_image = Gtk.Image.new_from_gicon(conf_icon, Gtk.IconSize.BUTTON)
        aconf_button = Gtk.Button()
        aconf_button.set_image(aconf_image)
        aconf_button.connect('clicked', self.on_conf_clicked, 'audio')

        self.queue_button = Gtk.Button('Queue')
        self.queue_button.set_property('hexpand', True)
        self.queue_button.set_sensitive(False)
        self.queue_button.connect('clicked', self.on_queue_clicked)

        vbox = Gtk.Box(spacing=6)
        vbox.pack_start(self.venc_cbtext, True, True, 0)
        vbox.pack_start(vconf_button, False, True, 0)

        abox = Gtk.Box(spacing=6)
        abox.pack_start(self.aenc_cbtext, True, True, 0)
        abox.pack_start(aconf_button, False, True, 0)

        input_grid = Gtk.Grid()
        input_grid.set_column_homogeneous(True)
        input_grid.set_column_spacing(6)
        input_grid.set_row_spacing(6)
        input_grid.attach(vpyconf_button, 0, 0, 1, 1)
        input_grid.attach_next_to(vbox, vpyconf_button,
                                  Gtk.PositionType.BOTTOM, 1, 1)
        input_grid.attach_next_to(abox, vbox,
                                  Gtk.PositionType.BOTTOM, 1, 1)
        input_grid.attach(hsep, 0, 3, 2, 1)
        input_grid.attach(out_grid, 1, 0, 1, 2)
        input_grid.attach_next_to(self.queue_button, out_grid,
                                  Gtk.PositionType.BOTTOM, 1, 1)

        # (enable, enable_edit, encode, encode_edit, type, codec, name, lang)
        self.track_lstore = Gtk.ListStore(bool, bool, bool, bool,
                                          str, str, str, str)

        enable_crtoggle = Gtk.CellRendererToggle()
        enable_crtoggle.connect('toggled', self.on_cell_toggled, 0)
        enable_tvcolumn = Gtk.TreeViewColumn('Enable', enable_crtoggle,
                                             active=0, activatable=1)

        encode_crtoggle = Gtk.CellRendererToggle()
        encode_crtoggle.connect('toggled', self.on_cell_toggled, 2)
        encode_tvcolumn = Gtk.TreeViewColumn('Encode', encode_crtoggle,
                                             active=2, activatable=3,
                                             sensitive=0)

        type_crtext = Gtk.CellRendererText()
        type_tvcolumn = Gtk.TreeViewColumn('Type', type_crtext, text=4,
                                           sensitive=0)

        format_crtext = Gtk.CellRendererText()
        format_tvcolumn = Gtk.TreeViewColumn('Format', format_crtext, text=5,
                                             sensitive=0)

        title_crtext = Gtk.CellRendererText()
        title_crtext.connect('edited', self.on_cell_edited, 6)
        title_tvcolumn = Gtk.TreeViewColumn('Title', title_crtext, text=6,
                                            editable=0, sensitive=0)
        title_tvcolumn.set_expand(True)

        lang_crtext = Gtk.CellRendererText()
        lang_crtext.connect('edited', self.on_cell_edited, 7)
        lang_tvcolumn = Gtk.TreeViewColumn('Language', lang_crtext, text=7,
                                           editable=0, sensitive=0)

        tview = Gtk.TreeView(self.track_lstore)
        tview.append_column(enable_tvcolumn)
        tview.append_column(encode_tvcolumn)
        tview.append_column(type_tvcolumn)
        tview.append_column(format_tvcolumn)
        tview.append_column(title_tvcolumn)
        tview.append_column(lang_tvcolumn)

        scrwin = Gtk.ScrolledWindow()
        scrwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        scrwin.add(tview)

        # --Queue-- #
        self.queue_tstore = Gtk.TreeStore(GObject.TYPE_PYOBJECT, str, str, str)

        qexp_crpixbuf = Gtk.CellRendererPixbuf()
        qexp_crpixbuf.set_property('is-expander', True)
        qexp_tvcolumn = Gtk.TreeViewColumn('', qexp_crpixbuf)

        qin_crtext = Gtk.CellRendererText()
        qin_tvcolumn = Gtk.TreeViewColumn('Input', qin_crtext, text=1)

        qcod_crtext = Gtk.CellRendererText()
        qcod_tvcolumn = Gtk.TreeViewColumn('Codec', qcod_crtext, text=2)

        qsta_crtext = Gtk.CellRendererText()
        qsta_tvcolumn = Gtk.TreeViewColumn('Status', qsta_crtext, text=3)

        queue_tview = Gtk.TreeView(self.queue_tstore)
        queue_tview.append_column(qexp_tvcolumn)
        queue_tview.append_column(qin_tvcolumn)
        queue_tview.append_column(qcod_tvcolumn)
        queue_tview.append_column(qsta_tvcolumn)

        queue_scrwin = Gtk.ScrolledWindow()
        queue_scrwin.set_policy(Gtk.PolicyType.AUTOMATIC,
                                Gtk.PolicyType.ALWAYS)
        queue_scrwin.add(queue_tview)

        self.queue_tselection = queue_tview.get_selection()

        self.queue_start_button = Gtk.Button()
        self.queue_start_button.set_label('Start')
        self.queue_start_button.connect('clicked', self.on_start_clicked)
        self.queue_start_button.set_sensitive(False)

        self.queue_stop_button = Gtk.Button()
        self.queue_stop_button.set_label('Stop')
        self.queue_stop_button.connect('clicked', self.on_stop_clicked)
        self.queue_stop_button.set_sensitive(False)

        self.queue_del_button = Gtk.Button()
        self.queue_del_button.set_label('Delete')
        self.queue_del_button.connect('clicked', self.on_del_clicked)
        self.queue_del_button.set_sensitive(False)

        self.queue_clr_button = Gtk.Button()
        self.queue_clr_button.set_label('Clear')
        self.queue_clr_button.connect('clicked', self.on_clr_clicked)
        self.queue_clr_button.set_sensitive(False)

        queue_ctl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                spacing=6)
        queue_ctl_box.pack_start(self.queue_start_button, True, True, 0)
        queue_ctl_box.pack_start(self.queue_stop_button, True, True, 0)
        queue_ctl_box.pack_start(self.queue_del_button, True, True, 0)
        queue_ctl_box.pack_start(self.queue_clr_button, True, True, 0)

        # --Notebook--#
        input_label = Gtk.Label('Input')
        queue_label = Gtk.Label('Queue')

        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        input_box.set_property('margin', 6)
        input_box.pack_start(input_grid, False, False, 0)
        input_box.pack_start(scrwin, True, True, 0)

        queue_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        queue_box.set_property('margin', 6)
        queue_box.pack_start(queue_scrwin, True, True, 0)
        queue_box.pack_start(queue_ctl_box, False, True, 0)

        notebook = Gtk.Notebook()
        notebook.append_page(input_box, input_label)
        notebook.append_page(queue_box, queue_label)

        for tab in notebook.get_children():
            notebook.child_set_property(tab, 'tab-expand', True)

        # --Progress Bar--#
        self.pbar = Gtk.ProgressBar()
        self.pbar.set_property('margin', 6)
        self.pbar.set_text('Ready')
        self.pbar.set_show_text(True)

        # --Main Box-- #
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.pack_start(notebook, True, True, 0)
        main_box.pack_start(self.pbar, False, True, 0)

        self.add(main_box)

        # --About Dialog-- #
        self.about_dlg = AboutDialog(self)
        self.about_dlg.set_transient_for(self)

    def on_sccr_clicked(self, button):
        sccr_win = ScriptCreatorWindow()
        sccr_win.show_all()

    def on_ched_clicked(self, button):
        ched_win = ChapterEditorWindow()
        ched_win.show_all()

    def on_about_clicked(self, button):
        self.about_dlg.run()
        self.about_dlg.hide()

    def on_cell_toggled(self, crtoggle, path, i):
        v = not self.track_lstore[path][i]
        self.track_lstore[path][i] = v

        t = self.tracklist[int(path)]
        if i == 0:
            t.enable = v
        elif i == 2:
            t.encode = v

    def on_cell_edited(self, crtext, path, v, i):
        self.track_lstore[path][i] = v

        t = self.tracklist[int(path)]
        if i == 6:
            t.title = v
        elif i == 7:
            # Language is a 3 letter code
            # TODO: write a custom cell renderer for this
            v = v[:3]
            t.lang = v

    def on_open_clicked(self, button):
        dlg = Gtk.FileChooserDialog('Select File(s)', self,
                                    Gtk.FileChooserAction.OPEN,
                                    ('Cancel',
                                     Gtk.ResponseType.CANCEL,
                                     'Open', Gtk.ResponseType.OK))
        dlg.set_property('select-multiple', True)
        dlg.add_filter(conf.vflt)
        dlg.set_current_folder(self.wdir)

        response = dlg.run()

        if response == Gtk.ResponseType.OK:
            self.track_lstore.clear()

            self.wdir = dlg.get_current_folder()
            self.files = dlg.get_filenames()

            if len(self.files) > 1:
                self.out_name_entry.set_text('')
                self.out_name_entry.set_sensitive(False)
            else:
                # Get the filename without extension
                out_name = os.path.splitext(os.path.basename(self.files[0]))[0]
                self.out_name_entry.set_text(out_name)
                self.out_name_entry.set_sensitive(True)

            self.tracklist = Parse(self.files[0]).get_tracklist()

            if self._check_consistency():
                self._populate_lstore()
                self.queue_button.set_sensitive(True)

        dlg.destroy()

    def _check_consistency(self):
        # Make sure tracks are identical across files
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO,
                                   Gtk.ButtonsType.OK, 'Track Mismatch')

        tracks_ref = self.tracklist
        o = os.path.basename(self.files[0])

        # Include first file in the loop for single files to pass the test
        for i in range(len(self.files)):
            tracks = Parse(self.files[i]).get_tracklist()
            f = os.path.basename(self.files[i])

            if len(tracks) != len(tracks_ref):
                t = ('{} ({} tracks) and {} ({} tracks) differ from each '
                     'other. Please make sure all files share the same '
                     'layout.'
                     ).format(o, str(len(tracks_ref)), f, str(len(tracks)))

                dialog.format_secondary_text(t)
                dialog.run()

            else:
                for j in range(len(tracks)):
                    ty_ref = tracks_ref[j].type
                    ty = tracks[j].type
                    fo_ref = tracks_ref[j].format
                    fo = tracks[j].format
                    la_ref = tracks_ref[j].lang
                    la = tracks[j].lang
                    if ty_ref == 'Audio':
                        ch_ref = tracks_ref[j].channels
                        ch = tracks[j].channels

                    if ty != ty_ref:
                        t = ('{} (track {}: {}) and {} (track {}: {}) have '
                             'different types. Please make sure all files '
                             'share the same layout.'
                             ).format(o, str(j), ty_ref, f, str(j), ty)
                    elif fo != fo_ref:
                        t = ('{} (track {}: {}) and {} (track {}: {}) have '
                             'different formats. Please make sure all files '
                             'share the same layout.'
                             ).format(o, str(j), fo_ref, f, str(j), fo)
                    elif la != la_ref:
                        t = ('{} (track {}: {}) and {} (track {}: {}) have '
                             'different languages. Please make sure all files '
                             'share the same layout.'
                             ).format(o, str(j), la_ref, f, str(j), la)
                    elif ty_ref == 'Audio' and ch != ch_ref:
                        t = ('{} (track {}: {}) and {} (track {}: {}) have '
                             'different channels. Please make sure all files '
                             'share the same layout.'
                             ).format(o, str(j), ch_ref, f, str(j), ch)
                    else:
                        return True

                    dialog.format_secondary_text(t)
                    dialog.run()
                    dialog.hide()

        dialog.destroy()

        return False

    def _populate_lstore(self):
        for t in self.tracklist:
            enable = t.enable
            enable_edit = False if t.type == 'Video' else True
            encode = t.encode
            track_type = t.type
            codec = t.format
            title = t.title
            lang = t.lang
            self.track_lstore.append([enable, enable_edit, encode, encode,
                                      track_type, codec, title, lang])

    def on_queue_clicked(self, button):
        for i in range(len(self.files)):
            vtrack = []
            atracks = []
            stracks = []
            mtracks = []

            in_dnx = self.files[i]
            in_nx = os.path.basename(in_dnx)
            in_dn, in_x = os.path.splitext(in_dnx)
            in_d, in_n = os.path.split(in_dn)
            tmp_d = in_dn + '.tmp'

            # Preserve UID for Matroska segment linking
            if in_x == '.mkv':
                uid = Parse(in_dnx).get_uid()
            else:
                uid = ''

            job = self.queue_tstore.append(None, [None, in_nx, '', 'Waiting'])

            for t in self.tracklist:
                if t.type == 'Video' and t.enable:
                    if t.encode:
                        # Encode video
                        k = self.venc_cbtext.get_active_text()
                        x = conf.VENCS[k]
                        # Create a local copy, otherwise all jobs will use the
                        # latest filter settings at runtime
                        flts = copy.deepcopy(conf.filters)

                        in_vpy = tmp_d + '/' + in_n + '.vpy'
                        future = self.worker.submit(self._vpy,
                                                    in_dnx,
                                                    in_vpy,
                                                    flts)

                        self.queue_tstore.append(job, [future,
                                                       '',
                                                       'vpy',
                                                       'Waiting'])

                        if x[0].startswith('x264'):
                            cfg = conf.x264
                            ext = cfg['container']
                            out = tmp_d + '/' + in_n + '.' + ext
                            future = self.worker.submit(self._x264,
                                                        in_vpy,
                                                        out,
                                                        x[0],
                                                        cfg['quality'],
                                                        cfg['preset'],
                                                        cfg['tune'],
                                                        cfg['arguments'])
                        elif x[0].startswith('x265'):
                            cfg = conf.x265
                            ext = cfg['container']
                            out = tmp_d + '/' + in_n + '.' + ext
                            future = self.worker.submit(self._x265,
                                                        in_vpy,
                                                        out,
                                                        x[0],
                                                        x[1],
                                                        cfg['quality'],
                                                        cfg['preset'],
                                                        cfg['tune'],
                                                        cfg['arguments'])

                        self.queue_tstore.append(job, [future,
                                                       '',
                                                       x[0],
                                                       'Waiting'])

                        vtrack = [0, out, t.title, t.lang]
                    else:
                        vtrack = [t.id, in_dnx, t.title, t.lang]

                elif t.type == 'Audio' and t.enable:
                    if t.encode:
                        # Encode audio
                        k = self.aenc_cbtext.get_active_text()
                        x = conf.AENCS[k]
                        o = '_'.join([in_n, str(t.id)])
                        at = [conf.audio['rate'], conf.audio['channel'],
                              conf.video['fpsnum'], conf.video['fpsden'],
                              conf.trim]

                        if x[0] == 'faac' or x[1] == 'libfaac':
                            cfg = conf.faac
                            ext = cfg['container']
                            out = tmp_d + '/' + o + '.' + ext
                            if x[0] == 'faac':
                                future = self.worker.submit(self._faac,
                                                            in_dnx,
                                                            out,
                                                            t.id,
                                                            cfg['mode'],
                                                            cfg['bitrate'],
                                                            cfg['quality'],
                                                            at)
                            elif x[0] == 'ffmpeg':
                                future = self.worker.submit(self._libfaac,
                                                            in_dnx,
                                                            out,
                                                            t.id,
                                                            cfg['mode'],
                                                            cfg['bitrate'],
                                                            cfg['quality'],
                                                            at)
                        elif x[0] == 'fdkaac' or x[1] == 'libfdk-aac':
                            cfg = conf.fdkaac
                            ext = cfg['container']
                            out = tmp_d + '/' + o + '.' + ext
                            if x[0] == 'fdkaac':
                                future = self.worker.submit(self._fdkaac,
                                                            in_dnx,
                                                            out,
                                                            t.id,
                                                            cfg['mode'],
                                                            cfg['bitrate'],
                                                            cfg['quality'],
                                                            at)
                            elif x[0] == 'ffmpeg':
                                future = self.worker.submit(self._libfdk_aac,
                                                            in_dnx,
                                                            out,
                                                            t.id,
                                                            cfg['mode'],
                                                            cfg['bitrate'],
                                                            cfg['quality'],
                                                            at)
                        elif x[0] == 'flac' or x[1] == 'native-flac':
                            cfg = conf.flac
                            ext = cfg['container']
                            out = tmp_d + '/' + o + '.' + ext
                            if x[0] == 'flac':
                                future = self.worker.submit(self._flac,
                                                            in_dnx,
                                                            out,
                                                            t.id,
                                                            cfg['compression'],
                                                            at)
                            elif x[0] == 'ffmpeg':
                                future = self.worker.submit(self._native_flac,
                                                            in_dnx,
                                                            out,
                                                            t.id,
                                                            cfg['compression'],
                                                            at)
                        elif x[0] == 'lame' or x[1] == 'libmp3lame':
                            cfg = conf.mp3
                            ext = cfg['container']
                            out = tmp_d + '/' + o + '.' + ext
                            if x[0] == 'lame':
                                future = self.worker.submit(self._lame,
                                                            in_dnx,
                                                            out,
                                                            t.id,
                                                            cfg['mode'],
                                                            cfg['bitrate'],
                                                            cfg['quality'],
                                                            at)
                            elif x[0] == 'ffmpeg':
                                future = self.worker.submit(self._libmp3lame,
                                                            in_dnx,
                                                            out,
                                                            t.id,
                                                            cfg['mode'],
                                                            cfg['bitrate'],
                                                            cfg['quality'],
                                                            at)
                        elif x[0] == 'opusenc' or x[1] == 'libopus':
                            cfg = conf.opus
                            ext = cfg['container']
                            out = tmp_d + '/' + o + '.' + ext
                            if x[0] == 'opusenc':
                                future = self.worker.submit(self._opusenc,
                                                            in_dnx,
                                                            out,
                                                            t.id,
                                                            cfg['mode'],
                                                            cfg['bitrate'],
                                                            at)
                            elif x[0] == 'ffmpeg':
                                future = self.worker.submit(self._libopus,
                                                            in_dnx,
                                                            out,
                                                            t.id,
                                                            cfg['mode'],
                                                            cfg['bitrate'],
                                                            at)
                        elif x[0] == 'oggenc' or x[1] == 'libvorbis':
                            cfg = conf.vorbis
                            ext = cfg['container']
                            out = tmp_d + '/' + o + '.' + ext
                            if x[0] == 'oggenc':
                                future = self.worker.submit(self._oggenc,
                                                            in_dnx,
                                                            out,
                                                            t.id,
                                                            cfg['mode'],
                                                            cfg['bitrate'],
                                                            cfg['quality'],
                                                            at)
                            elif x[0] == 'ffmpeg':
                                future = self.worker.submit(self._libvorbis,
                                                            in_dnx,
                                                            out,
                                                            t.id,
                                                            cfg['mode'],
                                                            cfg['bitrate'],
                                                            cfg['quality'],
                                                            at)

                        self.queue_tstore.append(job, [future,
                                                       '',
                                                       x[0],
                                                       'Waiting'])

                        atracks.append([0, out, t.title, t.lang])
                    else:
                        atracks.append([t.id, in_dnx, t.title, t.lang])

                elif t.type == 'Text' and t.enable:
                    stracks.append([t.id, in_dnx, t.title, t.lang])
                elif t.type == 'Menu' and t.enable:
                    mtracks.append([t.id, in_dnx, t.title, t.lang])

            # Merge tracks
            name = self.out_name_entry.get_text()
            suffix = self.out_suffix_entry.get_text()
            cont = self.out_cont_cbtext.get_active_text()

            if len(self.files) == 1 and name:
                out = '/'.join([in_d, name])
            else:
                out = in_dn
            # Do not overwrite source files in batch mode
            if len(self.files) > 1 and not suffix:
                suffix = 'new'
            out = '.'.join(['_'.join([out, suffix]), cont])

            future = self.worker.submit(self._merge, in_dnx, out,
                                        vtrack, atracks, stracks, mtracks, uid)

            self.queue_tstore.append(job, [future, '', 'merge', 'Waiting'])

            # Clean up
            self.worker.submit(self._clean, tmp_d)

            # Update queue
            self.worker.submit(self._update_queue)

            # Add a wait job after each encoding job
            future = self.worker.submit(self._wait)
            self.waitlist.append(future)

            if self.idle:
                self.queue_start_button.set_sensitive(True)
                self.queue_del_button.set_sensitive(True)
                self.queue_clr_button.set_sensitive(True)

    def on_conf_clicked(self, button, t):
        if t == 'input':
            dlg = VapourSynthDialog(self)
        else:
            if t == 'video':
                enc = self.venc_cbtext.get_active_text()
                enc = conf.VENCS[enc]
            elif t == 'audio':
                enc = self.aenc_cbtext.get_active_text()
                enc = conf.AENCS[enc]
            dlg = EncoderDialog(self, enc)

        dlg.run()
        dlg.destroy()

    def on_start_clicked(self, button):
        if len(self.queue_tstore):
            self.queue_stop_button.set_sensitive(True)
            self.queue_del_button.set_sensitive(False)
            self.queue_clr_button.set_sensitive(False)
            print('Start processing...')
            self.idle = False
            self.lock.release()

    def on_stop_clicked(self, button):
        tstore = self.queue_tstore
        self.idle = True
        print('Stop processing...')
        # Wait for the process to terminate
        while self.proc.poll() is None:
            self.proc.terminate()

        for job in tstore:
            status = tstore.get_value(job.iter, 3)
            if status == 'Running':
                for step in job.iterchildren():
                    future = tstore.get_value(step.iter, 0)
                    # Cancel and mark steps as failed
                    if not future.done():
                        tstore.set_value(step.iter, 3, 'Failed')
                        future.cancel()
                # Mark job as failed
                tstore.set_value(job.iter, 3, 'Failed')

        self.pbar.set_fraction(0)
        self.pbar.set_text('Ready')
        self.queue_stop_button.set_sensitive(False)
        self.queue_clr_button.set_sensitive(True)

    def on_del_clicked(self, button):
        tstore, job = self.queue_tselection.get_selected()
        # If child, select parent instead
        if tstore.iter_depth(job) == 1:
            job = tstore.iter_parent(job)
        status = tstore.get_value(job, 3)
        while tstore.iter_has_child(job):
            step = tstore.iter_nth_child(job, 0)
            future = tstore.get_value(step, 0)
            # Cancel pending step
            if not future.done():
                future.cancel()
            tstore.remove(step)
        # Cancel associated wait job
        if status not in ['Done', 'Failed']:
            idx = tstore.get_path(job).get_indices()[0]
            self.waitlist[idx].cancel()
        # Delete job
        tstore.remove(job)

        if not len(tstore):
            self.queue_start_button.set_sensitive(False)
            self.queue_del_button.set_sensitive(False)
            self.queue_clr_button.set_sensitive(False)

    def on_clr_clicked(self, button):
        tstore = self.queue_tstore
        for job in tstore:
            # Cancel jobs before clearing them
            for step in job.iterchildren():
                future = tstore.get_value(step.iter, 0)
                future.cancel()
            for future in self.waitlist:
                future.cancel()
        # Clear queue
        tstore.clear()

        self.queue_start_button.set_sensitive(False)
        self.queue_del_button.set_sensitive(False)
        self.queue_clr_button.set_sensitive(False)

    def _wait(self):
        if self.idle:
            self.lock.acquire()

    def _update_queue(self):
        tstore = self.queue_tstore
        for job in tstore:
            status = tstore.get_value(job.iter, 3)
            filename = tstore.get_value(job.iter, 1)
            new_status = self._mark_steps(job)
            GLib.idle_add(tstore.set_value, job.iter, 3, new_status)
            if new_status == 'Done' and not job.next:
                # Mark as idle if it was the last job
                GLib.idle_add(self._notify, 'Jobs done')
                self.idle = True
                self.queue_start_button.set_sensitive(False)
                self.queue_stop_button.set_sensitive(False)
                self.queue_clr_button.set_sensitive(True)
            elif new_status == 'Running' and new_status != status:
                GLib.idle_add(self._notify, 'Processing ' + filename)

    def _mark_steps(self, job):
        tstore = self.queue_tstore
        for step in job.iterchildren():
            future = tstore.get_value(step.iter, 0)
            status = tstore.get_value(step.iter, 3)
            if status == 'Failed':
                return 'Failed'
            elif future.done():
                # Mark done steps as such
                GLib.idle_add(tstore.set_value, step.iter, 3, 'Done')
                if not step.next:
                    # Mark job as done if all steps are
                    return 'Done'
            elif future.running():
                # Mark running step as such
                GLib.idle_add(tstore.set_value, step.iter, 3, 'Running')
                return 'Running'
            else:
                return 'Waiting'

    def _notify(self, text):
        self.notification.update('pyanimenc', text)
        self.notification.show()

    def _merge(self, i, o, vt, at, st, mt, uid):
        print('Merge...')
        self._update_queue()

        cmd = command.merge(i, o, vt, at, st, mt, uid)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                     universal_newlines=True)
        self._mkvtoolnix_progress()

    def _clean(self, d):
        print('Delete temporary files...')
        shutil.rmtree(d)

        GLib.add(self.pbar.set_fraction, 0)
        GLib.add(self.pbar.set_text, 'Ready')

    def _vpy(self, i, o, flts):
        print('Create VapourSynth script...')
        s = VapourSynthScript().script(i, flts)

        print('Write ' + o)
        tmp_d = os.path.dirname(o)
        if not os.path.isdir(tmp_d):
            os.mkdir(tmp_d)
        with open(o, 'w') as f:
            f.write(s)

    def _info(self, i):
        cmd = command.info(i)
        self.proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                     universal_newlines=True)
        GLib.idle_add(self.pbar.set_fraction, 0)
        GLib.idle_add(self.pbar.set_text, 'Encoding video...')
        while self.proc.poll() is None:
            line = self.proc.stdout.readline()
            # Get the frame total
            if 'Frames:' in line:
                dur = int(line.split(' ')[1])
        return dur

    def _x264(self, i, o, x, q, p, t, a):
        print('Encode video...')
        self._update_queue()
        dur = self._info(i)
        cmd = command.x264(i, o, x, q, p, t, a)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._video_progress(dur)

    def _x265(self, i, o, x, d, q, p, t, a):
        print('Encode video...')
        self._update_queue()
        dur = self._info(i)
        cmd = command.x265(i, o, x, d, q, p, t, a)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._video_progress(dur)

    def _faac(self, i, o, t, m, b, q, at):
        print('Encode audio...')
        self._update_queue()
        cmd = command.faac(i, o, t, m, b, q, at)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libfaac(self, i, o, t, m, b, q, at):
        print('Encode audio...')
        self._update_queue()
        cmd = command.ffmpeg_libfaac(i, o, t, m, b, q, at)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _fdkaac(self, i, o, t, m, b, q, at):
        print('Encode audio...')
        self._update_queue()
        cmd = command.fdkaac(i, o, t, m, b, q, at)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libfdk_aac(self, i, o, t, m, b, q, at):
        print('Encode audio...')
        self._update_queue()
        cmd = command.ffmpeg_libfdk_aac(i, o, t, m, b, q, at)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _flac(self, i, o, t, c, at):
        print('Encode audio...')
        self._update_queue()
        cmd = command.flac(i, o, t, c, at)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _native_flac(self, i, o, t, c, at):
        print('Encode audio...')
        self._update_queue()
        cmd = command.ffmpeg_flac(i, o, t, c, at)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _lame(self, i, o, t, m, b, q, at):
        print('Encode audio...')
        self._update_queue()
        cmd = command.lame(i, o, t, m, b, q, at)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libmp3lame(self, i, o, t, m, b, q, at):
        print('Encode audio...')
        self._update_queue()
        cmd = command.ffmpeg_libmp3lame(i, o, t, m, b, q, at)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _opusenc(self, i, o, t, m, b, at):
        print('Encode audio...')
        self._update_queue()
        cmd = command.opusenc(i, o, t, m, b, at)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libopus(self, i, o, t, m, b, at):
        print('Encode audio...')
        self._update_queue()
        cmd = command.ffmpeg_libopus(i, o, t, m, b, at)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _oggenc(self, i, o, t, m, b, q, at):
        print('Encode audio...')
        self._update_queue()
        cmd = command.oggenc(i, o, t, m, b, q, at)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libvorbis(self, i, o, t, m, b, q, at):
        print('Encode audio...')
        self._update_queue()
        cmd = command.ffmpeg_libvorbis(i, o, t, m, b, q, at)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _mkvtoolnix_progress(self):
        GLib.idle_add(self.pbar.set_fraction, 0)
        GLib.idle_add(self.pbar.set_text, 'Merging tracks...')
        while self.proc.poll() is None:
            line = self.proc.stdout.readline()
            if 'Progress:' in line:
                f = int(re.findall('[0-9]+', line)[0]) / 100
                GLib.idle_add(self.pbar.set_fraction, f)
        if self.proc.poll() < 0:
            GLib.idle_add(self.pbar.set_text, 'Failed')
        else:
            GLib.idle_add(self.pbar.set_text, 'Ready')
        GLib.idle_add(self.pbar.set_fraction, 0)

    def _video_progress(self, duration):
        while self.proc.poll() is None:
            line = self.proc.stderr.readline()
            # Get the current frame
            if re.match('^[0-9]+ ', line):
                position = int(line.split(' ')[0])
                f = round(position / duration, 2)
                GLib.idle_add(self.pbar.set_fraction, f)
        if self.proc.poll() < 0:
            GLib.idle_add(self.pbar.set_text, 'Failed')
        else:
            GLib.idle_add(self.pbar.set_text, 'Ready')
        GLib.idle_add(self.pbar.set_fraction, 0)

    def _audio_progress(self):
        GLib.idle_add(self.pbar.set_fraction, 0)
        GLib.idle_add(self.pbar.set_text, 'Encoding audio...')
        while self.proc.poll() is None:
            line = self.proc.stderr.readline()
            # Get the clip duration
            if 'Duration:' in line:
                d = re.findall('[0-9]{2}:[0-9]{2}:[0-9]{2}', line)[0]
                h, m, s = d.split(':')
                d = int(h) * 3600 + int(m) * 60 + int(s)
            # Get the current timestamp
            if 'time=' in line:
                p = re.findall('[0-9]{2}:[0-9]{2}:[0-9]{2}', line)[0]
                h, m, s = p.split(':')
                p = int(h) * 3600 + int(m) * 60 + int(s)
                f = round(p / d, 2)
                GLib.idle_add(self.pbar.set_fraction, f)
        if self.proc.poll() < 0:
            GLib.idle_add(self.pbar.set_text, 'Failed')
        else:
            GLib.idle_add(self.pbar.set_text, 'Ready')
        GLib.idle_add(self.pbar.set_fraction, 0)

    def on_delete_event(event, self, widget):
        tstore = self.queue_tstore
        # Cancel all jobs
        for job in tstore:
            for step in job.iterchildren():
                future = tstore.get_value(step.iter, 0)
                if not future.done():
                    future.cancel()
        for future in self.waitlist:
            future.cancel()
        Notify.uninit()
        self.lock.release()
        Gtk.main_quit()


class AboutDialog(Gtk.AboutDialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, parent)
        self.set_property('program-name', 'pyanimenc')
        self.set_property('version', VERSION)
        self.set_property('comments', 'Python Transcoding Tools')
        self.set_property('copyright', 'Copyright © 2014-2015 Maxime Gauduin')
        self.set_property('license-type', Gtk.License.GPL_3_0)
        self.set_property('website', 'https://github.com/alucryd/pyanimenc')

MainWindow().show_all()
Gtk.main()

# vim: ts=4 sw=4 et:
