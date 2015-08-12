#!/usr/bin/env python3

import os
import re
import pyanimenc.command as command
import pyanimenc.conf as conf
import subprocess
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from gi.repository import Gio, GLib, GObject, Gtk
from pyanimenc.chapter import ChapterEditorWindow
from pyanimenc.encoders import EncoderDialog
from pyanimenc.filters import FilterDialog
from pyanimenc.script import ScriptCreatorWindow
from pyanimenc.vapoursynth import VapourSynthDialog
from pyanimenc.vpy import vpy
from pymediainfo import MediaInfo
from threading import Lock

VERSION = '0.1b1'
AUTHOR = 'Maxime Gauduin <alucryd@gmail.com>'

class MainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title='pyanimenc')
        self.set_default_size(800, 600)

        #--Header Bar--#
        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.set_property('title', 'pyanimenc')

        tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        tools_box.set_property('margin', 6)
        tools_sccr_button = Gtk.Button()
        tools_sccr_button.set_label('Script Creator')
        tools_sccr_button.connect('clicked', self.on_sccr_clicked)
        tools_ched_button = Gtk.Button()
        tools_ched_button.set_label('Chapter Editor')
        tools_ched_button.connect('clicked', self.on_ched_clicked)
        tools_box.pack_start(tools_sccr_button, True, True, 0)
        tools_box.pack_start(tools_ched_button, True, True, 0)
        tools_box.show_all()

        tools_popover = Gtk.Popover()
        tools_popover.add(tools_box)

        tools_mbutton = Gtk.MenuButton()
        tools_mbutton.set_label('Tools')
        tools_mbutton.set_direction(Gtk.ArrowType.DOWN)
        tools_mbutton.set_use_popover(True)
        tools_mbutton.set_popover(tools_popover)

        about_button = Gtk.Button()
        about_button.set_label('About')
        about_button.connect('clicked', self.on_about_clicked)

        hbar.pack_start(tools_mbutton)
        hbar.pack_end(about_button)

        self.set_titlebar(hbar)

        #--Notebook--#
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        input_box.set_property('margin', 6)
        queue_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        queue_box.set_property('margin', 6)

        notebook = Gtk.Notebook()
        input_label = Gtk.Label('Input')
        notebook.append_page(input_box, input_label)
        queue_label = Gtk.Label('Queue')
        notebook.append_page(queue_box, queue_label)

        for tab in notebook.get_children():
            notebook.child_set_property(tab, 'tab-expand', True)

        main_box.pack_start(notebook, True, True, 0)

        #---Input---#
        input_grid = Gtk.Grid()
        input_grid.set_column_spacing(6)
        input_grid.set_row_spacing(6)

        conf_icon = Gio.ThemedIcon(name='applications-system-symbolic')
        queue_icon = Gio.ThemedIcon(name='list-add-symbolic')

        manual_label = Gtk.Label()
        manual_label.set_markup('<b>Manual</b>')
        manual_label.set_halign(Gtk.Align.CENTER)
        vid_label = Gtk.Label('Video')
        vid_label.set_angle(90)
        aud_label = Gtk.Label('Audio')
        aud_label.set_angle(90)

        self.vsrc_fcbutton = Gtk.FileChooserButton()
        self.vsrc_fcbutton.set_property('hexpand', True)
        self.vsrc_fcbutton.add_filter(conf.sflt)
        self.vsrc_fcbutton.connect('file-set', self.on_vsrc_file_set)
        self.asrc_fcbutton = Gtk.FileChooserButton()
        self.asrc_fcbutton.set_property('hexpand', True)
        self.asrc_fcbutton.add_filter(conf.aflt)
        self.asrc_fcbutton.connect('file-set', self.on_asrc_file_set)

        self.venc_cbtext = Gtk.ComboBoxText()
        self.venc_cbtext.set_property('hexpand', True)
        self.aenc_cbtext = Gtk.ComboBoxText()
        self.aenc_cbtext.set_property('hexpand', True)

        vqueue_image = Gtk.Image.new_from_gicon(queue_icon,
                                                Gtk.IconSize.BUTTON)
        self.vqueue_button = Gtk.Button()
        self.vqueue_button.set_image(vqueue_image)
        self.vqueue_button.set_sensitive(False)
        self.vqueue_button.connect('clicked', self.on_vqueue_clicked)
        vconf_image = Gtk.Image.new_from_gicon(conf_icon, Gtk.IconSize.BUTTON)
        self.vconf_button = Gtk.Button()
        self.vconf_button.set_image(vconf_image)
        self.vconf_button.connect('clicked', self.on_conf_clicked, 'manual',
                                  'video')
        aqueue_image = Gtk.Image.new_from_gicon(queue_icon,
                                                Gtk.IconSize.BUTTON)
        self.aqueue_button = Gtk.Button()
        self.aqueue_button.set_image(aqueue_image)
        self.aqueue_button.set_sensitive(False)
        self.aqueue_button.connect('clicked', self.on_aqueue_clicked)
        aconf_image = Gtk.Image.new_from_gicon(conf_icon, Gtk.IconSize.BUTTON)
        self.aconf_button = Gtk.Button()
        self.aconf_button.set_image(aconf_image)
        self.aconf_button.connect('clicked', self.on_conf_clicked, 'manual',
                                  'audio')

        vsep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        hsep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

        auto_label = Gtk.Label()
        auto_label.set_markup('<b>One-Click</b>')
        auto_label.set_halign(Gtk.Align.CENTER)

        self.auto_src_fcbutton = Gtk.FileChooserButton()
        self.auto_src_fcbutton.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        self.auto_src_fcbutton.set_property('hexpand', True)
        self.auto_src_fcbutton.connect('file-set', self.on_auto_src_file_set)

        self.auto_venc_cbtext = Gtk.ComboBoxText()
        self.auto_venc_cbtext.set_property('hexpand', True)
        self.auto_aenc_cbtext = Gtk.ComboBoxText()
        self.auto_aenc_cbtext.set_property('hexpand', True)

        auto_sconf_image = Gtk.Image.new_from_gicon(conf_icon,
                                                    Gtk.IconSize.BUTTON)
        auto_sconf_button = Gtk.Button()
        auto_sconf_button.set_image(auto_sconf_image)
        auto_sconf_button.connect('clicked', self.on_auto_sconf_clicked)
        auto_vconf_image = Gtk.Image.new_from_gicon(conf_icon,
                                                    Gtk.IconSize.BUTTON)
        auto_vconf_button = Gtk.Button()
        auto_vconf_button.set_image(auto_vconf_image)
        auto_vconf_button.connect('clicked', self.on_conf_clicked, 'auto',
                                  'video')
        auto_aconf_image = Gtk.Image.new_from_gicon(conf_icon,
                                                    Gtk.IconSize.BUTTON)
        auto_aconf_button = Gtk.Button()
        auto_aconf_button.set_image(auto_aconf_image)
        auto_aconf_button.connect('clicked', self.on_conf_clicked, 'auto',
                                  'audio')

        auto_queue_image = Gtk.Image.new_from_gicon(queue_icon,
                                                    Gtk.IconSize.BUTTON)
        self.auto_queue_button = Gtk.Button()
        self.auto_queue_button.set_image(auto_queue_image)
        self.auto_queue_button.set_sensitive(False)
        self.auto_queue_button.connect('clicked', self.on_auto_queue_clicked)

        input_grid.attach(manual_label, 0, 0, 3, 1)
        input_grid.attach(vid_label, 0, 1, 1, 2)
        input_grid.attach(self.vsrc_fcbutton, 1, 1, 1, 1)
        input_grid.attach_next_to(self.vqueue_button, self.vsrc_fcbutton,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(self.venc_cbtext, 1, 2, 1, 1)
        input_grid.attach_next_to(self.vconf_button, self.venc_cbtext,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(aud_label, 0, 3, 1, 2)
        input_grid.attach(self.asrc_fcbutton, 1, 3, 1, 1)
        input_grid.attach_next_to(self.aqueue_button, self.asrc_fcbutton,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(self.aenc_cbtext, 1, 4, 1, 1)
        input_grid.attach_next_to(self.aconf_button, self.aenc_cbtext,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(vsep, 3, 0, 1, 5)
        input_grid.attach(auto_label, 4, 0, 2 ,1)
        input_grid.attach(self.auto_src_fcbutton, 4, 1, 1, 1)
        input_grid.attach_next_to(auto_sconf_button, self.auto_src_fcbutton,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(self.auto_venc_cbtext, 4, 2, 1, 1)
        input_grid.attach_next_to(auto_vconf_button, self.auto_venc_cbtext,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(self.auto_aenc_cbtext, 4, 3, 1, 1)
        input_grid.attach_next_to(auto_aconf_button, self.auto_aenc_cbtext,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(self.auto_queue_button, 4, 4, 2, 1)
        input_grid.attach(hsep, 0, 5, 6, 1)

        auto_scrwin = Gtk.ScrolledWindow()
        auto_scrwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)

        #(enable, enable_edit, encode, encode_edit, type, codec, name,
        # language)
        self.tracks = Gtk.ListStore(bool, bool, bool, bool, str, str, str, str)

        auto_tview = Gtk.TreeView(self.tracks)
        auto_scrwin.add(auto_tview)

        enable_crtoggle = Gtk.CellRendererToggle()
        enable_tvcolumn = Gtk.TreeViewColumn('Enable', enable_crtoggle,
                                             active=0, activatable=1)
        enable_crtoggle.connect('toggled', self.on_cell_toggled, 0)
        auto_tview.append_column(enable_tvcolumn)

        encode_crtoggle = Gtk.CellRendererToggle()
        encode_tvcolumn = Gtk.TreeViewColumn('Encode', encode_crtoggle,
                                             active=2, activatable=3,
                                             sensitive=0)
        encode_crtoggle.connect('toggled', self.on_cell_toggled, 2)
        auto_tview.append_column(encode_tvcolumn)

        codec_crtext = Gtk.CellRendererText()
        codec_tvcolumn = Gtk.TreeViewColumn('Codec', codec_crtext, text=5,
                                            sensitive=0)
        auto_tview.append_column(codec_tvcolumn)

        title_crtext = Gtk.CellRendererText()
        title_tvcolumn = Gtk.TreeViewColumn('Title', title_crtext, text=6,
                                            editable=0, sensitive=0)
        title_tvcolumn.set_expand(True)
        title_crtext.connect('edited', self.on_cell_edited, 6)
        auto_tview.append_column(title_tvcolumn)

        lang_crtext = Gtk.CellRendererText()
        lang_tvcolumn = Gtk.TreeViewColumn('Language', lang_crtext, text=7,
                                           editable=0, sensitive=0)
        lang_crtext.connect('edited', self.on_cell_edited, 7)
        auto_tview.append_column(lang_tvcolumn)

        input_box.pack_start(input_grid, False, False, 0)
        input_box.pack_start(auto_scrwin, True, True, 0)

        #--Worker--#
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.idle = True
        self.lock = Lock()
        self.lock.acquire()

        #--Queue--#
        self.queue_tstore = Gtk.TreeStore(GObject.TYPE_PYOBJECT, str, str, str)

        queue_scrwin = Gtk.ScrolledWindow()
        queue_scrwin.set_policy(Gtk.PolicyType.AUTOMATIC,
                                Gtk.PolicyType.ALWAYS)
        queue_tview = Gtk.TreeView(self.queue_tstore)
        self.queue_tselection = queue_tview.get_selection()
        queue_scrwin.add(queue_tview)

        qexp_crpixbuf = Gtk.CellRendererPixbuf()
        qexp_crpixbuf.set_property('is-expander', True)
        qexp_tvcolumn = Gtk.TreeViewColumn('', qexp_crpixbuf)
        queue_tview.append_column(qexp_tvcolumn)

        qsrc_crtext = Gtk.CellRendererText()
        qsrc_tvcolumn = Gtk.TreeViewColumn('Source', qsrc_crtext, text=1)
        queue_tview.append_column(qsrc_tvcolumn)

        qcod_crtext = Gtk.CellRendererText()
        qcod_tvcolumn = Gtk.TreeViewColumn('Codec', qcod_crtext, text=2)
        queue_tview.append_column(qcod_tvcolumn)

        qsta_crtext = Gtk.CellRendererText()
        qsta_tvcolumn = Gtk.TreeViewColumn('Status', qsta_crtext, text=3)
        queue_tview.append_column(qsta_tvcolumn)

        queue_start_button = Gtk.Button()
        queue_start_button.set_label('Start')
        queue_start_button.connect('clicked', self.on_start_clicked)
        queue_stop_button = Gtk.Button()
        queue_stop_button.set_label('Stop')
        queue_stop_button.connect('clicked', self.on_stop_clicked)
        queue_del_button = Gtk.Button()
        queue_del_button.set_label('Delete')
        queue_del_button.connect('clicked', self.on_del_clicked)
        queue_clr_button = Gtk.Button()
        queue_clr_button.set_label('Clear')
        queue_clr_button.connect('clicked', self.on_clr_clicked)

        queue_ctl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                spacing=6)
        queue_ctl_box.pack_start(queue_start_button, True, True, 0)
        queue_ctl_box.pack_start(queue_stop_button, True, True, 0)
        queue_ctl_box.pack_start(queue_del_button, True, True, 0)
        queue_ctl_box.pack_start(queue_clr_button, True, True, 0)

        queue_box.pack_start(queue_scrwin, True, True, 0)
        queue_box.pack_start(queue_ctl_box, False, True, 0)

        #--Progress Bar--#
        self.pbar = Gtk.ProgressBar()
        self.pbar.set_property('margin', 6)
        self.pbar.set_text('Ready')
        self.pbar.set_show_text(True)

        main_box.pack_start(self.pbar, False, True, 0)

        self.add(main_box)

        #--Encoders--#
        for x in conf.VENCS:
            self.venc_cbtext.append_text(x)
            self.venc_cbtext.set_active(0)
            self.auto_venc_cbtext.append_text(x)
            self.auto_venc_cbtext.set_active(0)
        for x in conf.AENCS:
            self.aenc_cbtext.append_text(x)
            self.aenc_cbtext.set_active(0)
            self.auto_aenc_cbtext.append_text(x)
            self.auto_aenc_cbtext.set_active(0)

        self.about_dlg = AboutDialog(self)
        self.about_dlg.set_transient_for(self)

    def on_sccr_clicked(self, button):
        win = ScriptCreatorWindow(conf.vs)
        win.show_all()

    def on_ched_clicked(self, button):
        win = ChapterEditorWindow()
        win.show_all()

    def on_about_clicked(self, button):
        self.about_dlg.run()
        self.about_dlg.hide()

    def on_cell_toggled(self, crtoggle, path, i):
        self.tracks[path][i] = not self.tracks[path][i]

    def on_cell_edited(self, crtext, path, t, i):
        # Language is a 3 letter code
        # TODO: write a custom cell renderer for this
        if i == 4:
            t = t[:3]
        self.tracks[path][i] = t

    def on_vsrc_file_set(self, button):
        self.vqueue_button.set_sensitive(True)

    def on_vqueue_clicked(self, button):
        self.worker.submit(self._wait)
        k = self.venc_cbtext.get_active_text()
        x = conf.VENCS[k]
        i = self.vsrc_fcbutton.get_filename()
        wd, f = os.path.split(i)
        if not os.path.isdir(wd + '/out'):
            os.mkdir(wd + '/out')
        o = wd + '/out/' + os.path.splitext(f)[0]
        future = self._video_job(x, i, o)
        self.queue_tstore.append(None, [future, f, x[0], 'Waiting'])
        self.worker.submit(self._update_queue)

    def _video_job(self, x, i, o):
        if x[0].startswith('x264'):
            q = conf.x264['quality']
            p = conf.x264['preset']
            t = conf.x264['tune']
            c = conf.x264['container']
            a = conf.x264['arguments']
            future = self.worker.submit(self._x264, i, o, x[0], q, p, t, c, a)
        elif x[0].startswith('x265'):
            q = conf.x265['quality']
            p = conf.x265['preset']
            t = conf.x265['tune']
            c = conf.x265['container']
            a = conf.x265['arguments']
            future = self.worker.submit(self._x265, i, o, x[0], x[1], q, p, t,
                                        c, a)
        return future

    def on_asrc_file_set(self, button):
        self.aqueue_button.set_sensitive(True)

    def on_aqueue_clicked(self, button):
        self.worker.submit(self._wait)
        k = self.aenc_cbtext.get_active_text()
        x = conf.AENCS[k]
        i = self.asrc_fcbutton.get_filename()
        wd, f = os.path.split(i)
        if not os.path.isdir(wd + '/out'):
            os.mkdir(wd + '/out')
        o = wd + '/out/' + os.path.splitext(f)[0]
        future = self._audio_job(x, i, 0, o)
        self.queue_tstore.append(None, [future, f, x[0], 'Waiting'])
        self.worker.submit(self._update_queue)

    def _audio_job(self, x, i, t, o):
        r = conf.audio['rate']
        c = conf.audio['channel']
        if x[0] == 'faac' or x[1] == 'libfaac':
            m = conf.faac['mode']
            b = conf.faac['bitrate']
            q = conf.faac['quality']
            co = conf.faac['container']
            if x[0] == 'faac':
                future = self.worker.submit(self._faac, i, o, t,
                                            r, c, m, b, q, co)
            elif x[0] == 'ffmpeg':
                future = self.worker.submit(self._libfaac, i, o, t,
                                            r, c, m, b, q, co)
        elif x[0] == 'fdkaac' or x[1] == 'libfdk-aac':
            m = conf.fdkaac['mode']
            b = conf.fdkaac['bitrate']
            q = conf.fdkaac['quality']
            co = conf.fdkaac['container']
            if x[0] == 'fdkaac':
                future = self.worker.submit(self._fdkaac, i, o, t,
                                            r, c, m, b, q, co)
            elif x[0] == 'ffmpeg':
                future = self.worker.submit(self._libfdk_aac, i, o, t,
                                            r, c, m, b, q, co)
        elif x[0] == 'flac' or x[1] == 'native-flac':
            cp = conf.flac['compression']
            co = conf.flac['container']
            if x[0] == 'flac':
                future = self.worker.submit(self._flac, i, o, t,
                                            r, c, cp, co)
            elif x[0] == 'ffmpeg':
                future = self.worker.submit(self._native_flac, i, o, t,
                                            r, c, cp, co)
        elif x[0] == 'lame' or x[1] == 'libmp3lame':
            m = conf.mp3['mode']
            b = conf.mp3['bitrate']
            q = conf.mp3['quality']
            co = conf.mp3['container']
            if x[0] == 'lame':
                future = self.worker.submit(self._lame, i, o, t,
                                            r, c, m, b, q, co)
            elif x[0] == 'ffmpeg':
                future = self.worker.submit(self._libmp3lame, i, o, t,
                                            r, c, m, b, q, co)
        elif x[0] == 'opusenc' or x[1] == 'libopus':
            m = conf.opus['mode']
            b = conf.opus['bitrate']
            co = conf.opus['container']
            if x[0] == 'opusenc':
                future = self.worker.submit(self._opusenc, i, o, t,
                                            r, c, m, b, co)
            elif x[0] == 'ffmpeg':
                future = self.worker.submit(self._libopus, i, o, t,
                                            r, c, m, b, co)
        elif x[0] == 'oggenc' or x[1] == 'libvorbis':
            m = conf.vorbis['mode']
            b = conf.vorbis['bitrate']
            q = conf.vorbis['quality']
            co = conf.vorbis['container']
            if x[0] == 'oggenc':
                future = self.worker.submit(self._oggenc, i, o, t,
                                            r, c, m, b, q, co)
            elif x[0] == 'ffmpeg':
                future = self.worker.submit(self._libvorbis, i, o, t,
                                            r, c, m, b, q, co)
        return future

    def on_auto_src_file_set(self, button):
        wd = button.get_filename()
        self.sources = []
        self.data = []
        self.tracks.clear()

        # Keep MKVs only (for now?)
        for f in os.listdir(wd):
            if re.search('\.mkv$', f):
                f = wd + '/' + f
                self.sources.append(f)
        self.sources.sort()

        # Get source infos
        for i in range(len(self.sources)):
            s = self.sources[i]
            d = MediaInfo.parse(s)
            self.data.append(d)

        # Pick reference tracks
        tracks_ref = self.data[0].tracks

        # Make sure tracks are identical across files
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO,
                                   Gtk.ButtonsType.OK, 'Track Mismatch')

        for i in range(1, len(self.data)):
            tracks = self.data[i].tracks
            o = os.path.basename(self.sources[0])
            f = os.path.basename(self.sources[i])

            if len(tracks) != len(tracks_ref):
                t = ('{} ({} tracks) and {} ({} tracks) differ from each '
                     'other. Please make sure all files share the same '
                     'layout.'
                    ).format(o, str(len(tracks_ref)), f, str(len(tracks)))

                dialog.format_secondary_text(t)
                dialog.run()

            # First track contains general information
            for j in range(1, len(tracks)):
                codec_ref = tracks_ref[j].codec
                language_ref = tracks_ref[j].language
                channels_ref = tracks_ref[j].channel_s
                codec = tracks[j].codec
                language = tracks[j].language
                channels = tracks[j].channel_s

                if codec != codec_ref:
                    t = ('{} (track {}: {}) and {} (track {}: {}) have '
                         'different codecs. Please make sure all files '
                         'share the same layout.'
                        ).format(o, str(j), codec_ref, f, str(j), codec)

                    dialog.format_secondary_text(t)
                    dialog.run()

                elif language != language_ref:
                    t = ('{} (track {}: {}) and {} (track {}: {}) have '
                         'different languages. Please make sure all files '
                         'share the same layout.'
                        ).format(o, str(j), language_ref, f, str(j), language)

                    dialog.format_secondary_text(t)
                    dialog.run()

                elif channels != channels_ref:
                    t = ('{} (track {}: {}) and {} (track {}: {}) have '
                         'different channels. Please make sure all files '
                         'share the same layout.'
                        ).format(o, str(j), channels_ref, f, str(j), channels)

                    dialog.format_secondary_text(t)
                    dialog.run()

                dialog.hide()

        dialog.destroy()

        for i in range(1, len(tracks_ref)):
            enable = True
            enable_edit = True
            encode = True
            encode_edit = True

            track = tracks_ref[i]
            track_type = track.track_type
            codec = track.codec_family
            title = track.title
            language = track.other_language

            if language:
                language = language[3]
            else:
                language = 'und'

            #if track_type == 'Audio':
            #channels = track.channel_s
            #sampling_rate = track.sampling_rate
            #    if channels == '1':
            #        channels = '1.0'
            #    elif channels == '2':
            #        channels = '2.0'
            #    elif channels == '5':
            #        channels = '5.0'
            #    elif channels == '6':
            #        channels = '5.1'
            #    elif channels == '7':
            #        channels = '6.1'
            #    elif channels == '8':
            #        channels = '7.1'

            if track_type == 'Subtitle':
                encode = False
                encode_edit = False

            self.tracks.append([enable, enable_edit, encode, encode_edit,
                                     track_type, codec, title, language])

        self.auto_queue_button.set_sensitive(True)

    def on_auto_queue_clicked(self, button):
        wd = self.auto_src_fcbutton.get_filename()
        if not os.path.isdir(wd + '/out'):
            os.mkdir(wd + '/out')

        for i in range(len(self.sources)):
            self.worker.submit(self._wait)
            vtrack = []
            atracks = []
            stracks = []
            source = self.sources[i]
            filename = os.path.basename(source)
            destination = wd + '/out/' + filename
            basename, extension = os.path.splitext(filename)
            extension = extension.strip('.')
            job = self.queue_tstore.append(None, [None, filename, '',
                                                  'Waiting'])

            # Preserve UID for Matroska segment linking
            if extension == 'mkv':
                uid = self.data[i].tracks[0].other_unique_id[0]
                uid = re.findall('0x[^)]*', uid)[0].lstrip('0x')
            else:
                uid = ''

            for j in range(len(self.tracks)):
                #(enable, enable_edit, encode, encode_edit, type, codec, title,
                # language)
                # {v,a,s}track = [id, filename, extension, name, language,
                #                 encode]
                track = self.tracks[j]
                enable = track[0]
                encode = track[2]
                track_type = track[4]
                codec = track[5]
                title = track[6]
                language = track[7]
                if track_type == 'Video' and enable:
                    if encode:
                        f = wd + '/out/' + basename
                    else:
                        f = wd + '/' + basename
                    vtrack = [j, f, extension, title, language, encode]
                if track_type == 'Audio' and enable:
                    if encode:
                        f = wd + '/out/' + basename + '_' + str(j)
                    else:
                        f = wd + '/' + basename
                    atracks.append([j, f, extension, title, language, encode])
                if track_type == 'Subtitle' and enable:
                    f = wd + '/' + basename
                    stracks.append([j, f, extension, name, lang, encode])

            if vtrack[5]:
                # Create VapourSynth script
                s = wd + '/out/' + basename + '.vpy'

                self.worker.submit(self._vpy, source, s)

                # Encode video
                k = self.auto_venc_cbtext.get_active_text()
                x = conf.VENCS[k]
                o = vtrack[1]

                if x[0].startswith('x264'):
                    c = conf.x264['container']
                elif x[0].startswith('x265'):
                    c = conf.x265['container']
                vtrack[2] = c

                future = self._video_job(x, s, o)
                self.queue_tstore.append(job, [future, '', x[0], 'Waiting'])

            # Encode audio
            for track in atracks:
                if track[5]:
                    k = self.auto_aenc_cbtext.get_active_text()
                    x = conf.AENCS[k]
                    t = track[0]
                    o = track[1]

                    if x[0] == 'faac' or x[1] == 'libfaac':
                        c = conf.faac['container']
                    elif x[0] == 'fdkaac' or x[1] == 'libfdk-aac':
                        c = conf.fdkaac['container']
                    elif x[0] == 'flac' or x[1] == 'native-flac':
                        c = conf.flac['container']
                    elif x[0] == 'lame' or x[1] == 'libmp3lame':
                        c = conf.mp3['container']
                    elif x[0] == 'opusenc' or x[1] == 'libopus':
                        c = conf.opus['container']
                    elif x[0] == 'oggenc' or x[1] == 'libvorbis':
                        c = conf.vorbis['container']
                    track[2] = c

                    future = self._audio_job(x, source, t, o)
                    self.queue_tstore.append(job, [future, '', x[0],
                                             'Waiting'])

            # Merge tracks
            future = self.worker.submit(self._merge, source, destination,
                                        vtrack, atracks, stracks, uid)

            self.queue_tstore.append(job, [future, '', 'merge', 'Waiting'])

            # Clean up
            self.worker.submit(self._clean, wd)

            self.worker.submit(self._update_queue)

    def on_conf_clicked(self, button, m, t):
        if m == 'manual':
            if t == 'video':
                enc = self.venc_cbtext.get_active_text()
                enc = conf.VENCS[enc]
            elif t == 'audio':
                enc = self.aenc_cbtext.get_active_text()
                enc = conf.AENCS[enc]
        elif m == 'auto':
            if t == 'video':
                enc = self.auto_venc_cbtext.get_active_text()
                enc = conf.VENCS[enc]
            elif t == 'audio':
                enc = self.auto_aenc_cbtext.get_active_text()
                enc = conf.AENCS[enc]

        dlg = EncoderDialog(self, enc)
        dlg.run()
        dlg.destroy()

    def on_auto_sconf_clicked(self, button):
        dlg = VapourSynthDialog(self)
        dlg.run()
        dlg.destroy()

    def on_start_clicked(self, button):
        if len(self.queue_tstore):
            print('Start processing...')
            self.idle = False
            self.lock.release()

    def on_stop_clicked(self, button):
        if not self.idle:
            print('Stop processing...')
            self.idle = True
            # Wait for the process to terminate
            while self.proc.poll() == None:
                self.proc.terminate()

            njobs = len(self.queue_tstore)
            for i in range(njobs):
                path = Gtk.TreePath(i)
                job = self.queue_tstore.get_iter(path)
                status = self.queue_tstore.get_value(job, 3)
                if status == 'Running':
                    if self.queue_tstore.iter_has_child(job):
                        nsteps = self.queue_tstore.iter_n_children(job)
                        for j in range(nsteps):
                            path = Gtk.TreePath([i, j])
                            step = self.queue_tstore.get_iter(path)
                            future = self.queue_tstore.get_value(step, 0)
                            # Mark children as failed
                            self.queue_tstore.set_value(step, 3, 'Failed')
                            # Cancel pending children
                            if not future.done():
                                future.cancel()
                    # Mark job as failed
                    self.queue_tstore.set_value(job, 3, 'Failed')

            self.pbar.set_fraction(0)
            self.pbar.set_text('Ready')

    def on_del_clicked(self, button):
        job = self.queue_tselection.get_selected()[1]
        if job != None:
            # If child, select parent instead
            if self.queue_tstore.iter_depth(job) == 1:
                job = self.queue_tstore.iter_parent(job)
            # If parent, delete all children
            if self.queue_tstore.iter_has_child(job):
                nsteps = self.queue_tstore.iter_n_children(job)
                for i in range(nsteps):
                    step = self.queue_tstore.iter_nth_child(job, 0)
                    future = self.queue_tstore.get_value(step, 0)
                    # Cancel and delete child only if not running
                    if not future.running():
                        future.cancel()
                        self.queue_tstore.remove(step)
                # Delete parent only when all children are
                if not self.queue_tstore.iter_has_child(job):
                    self.queue_tstore.remove(job)
            else:
                future = self.queue_tstore.get_value(job, 0)
                # Cancel and delete job only if not running
                if not future.running():
                    future.cancel()
                    self.queue_tstore.remove(job)

    def on_clr_clicked(self, button):
        # Don't clear when jobs are running
        if self.idle:
            njobs = len(self.queue_tstore)
            for i in range(njobs):
                path = Gtk.TreePath(i)
                job = self.queue_tstore.get_iter(path)
                # Clear children before parents
                if self.queue_tstore.iter_has_child(job):
                    nsteps = self.queue_tstore.iter_n_children(job)
                    for j in range(nsteps):
                        path = Gtk.TreePath([i, j])
                        step = self.queue_tstore.get_iter(path)
                        future = self.queue_tstore.get_value(step, 0)
                        # Cancel pending children before deleting them
                        if not future.done():
                            future.cancel()
                else:
                    future = self.queue_tstore.get_value(job, 0)
                    # Cancel pending jobs before deleting them
                    if not future.done():
                        future.cancel()
            # Clear queue
            self.queue_tstore.clear()

    def _wait(self):
        if self.idle:
            self.lock.acquire()
        else:
            self.lock.release()

    def _update_queue(self):
        njobs = len(self.queue_tstore)
        for i in range(njobs):
            path = Gtk.TreePath(i)
            job = self.queue_tstore.get_iter(path)
            future = self.queue_tstore.get_value(job, 0)
            status = self.queue_tstore.get_value(job, 3)
            if self.queue_tstore.iter_has_child(job):
                nsteps = self.queue_tstore.iter_n_children(job)
                for j in range(nsteps):
                    path = Gtk.TreePath([i, j])
                    step = self.queue_tstore.get_iter(path)
                    future = self.queue_tstore.get_value(step, 0)
                    status = self.queue_tstore.get_value(step, 3)
                    # Mark done children as such
                    if future.done() and status != 'Failed':
                        GLib.idle_add(self.queue_tstore.set_value, step, 3,
                                      'Done')
                        # Mark parent as done if all children are
                        if j == nsteps - 1:
                            GLib.idle_add(self.queue_tstore.set_value, job, 3,
                                          'Done')
                            # Mark as idle if child was the last job
                            if i == njobs - 1:
                                self.idle = True
                    # Mark running child as such
                    elif future.running():
                        GLib.idle_add(self.queue_tstore.set_value, step, 3,
                                      'Running')
                        # Mark parent as running if a child is
                        GLib.idle_add(self.queue_tstore.set_value, job, 3,
                                      'Running')
            else:
                # Mark done jobs as such
                if future.done() and status != 'Failed':
                    GLib.idle_add(self.queue_tstore.set_value, job, 3,
                                  'Done')
                    # Mark as idle if job was the last
                    if i == njobs - 1:
                        self.idle = True
                # Mark running job as such
                elif future.running():
                    GLib.idle_add(self.queue_tstore.set_value, job, 3,
                                  'Running')

    def _merge(self, i, o, vt, at, st, uid):
        print('Merge...')
        self._update_queue()

        if vt[5]:
            vt[0] = 0
        for t in at:
            if t[5]:
                t[0] = 0

        cmd = command.merge(i, o, vt, at, st, uid)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                     universal_newlines=True)
        self._mkvtoolnix_progress('m')

    def _clean(self, d):
        print('Clean leftovers...')
        for f in os.listdir(d):
            if f.endswith('.ffindex'):
                os.remove(d + '/' + f)
        d = d + '/out'
        for f in os.listdir(d):
            if not f.endswith('.mkv'):
                os.remove(d + '/' + f)

        Glid.add(self.pbar.set_fraction, 0)
        Glib.add(self.pbar.set_text, 'Ready')

    def _vpy(self, i, o):
        print('Create VapourSynth script...')
        s = vpy(i, conf.vs)

        print('Write ' + o)
        with open(o, 'w') as f:
            f.write(s)

    def _info(self, i):
        cmd = command.info(i)
        self.proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                     universal_newlines=True)
        GLib.idle_add(self.pbar.set_fraction, 0)
        GLib.idle_add(self.pbar.set_text, 'Encoding video...')
        while self.proc.poll() == None:
            line = self.proc.stdout.readline()
            # Get the frame total
            if 'Frames:' in line:
                dur = int(line.split(' ')[1])
        return dur

    def _x264(self, i, o, x, q, p, t, c, a):
        print('Encode video...')
        self._update_queue()
        dur = self._info(i)
        cmd = command.x264(i, o, x, q, p, t, c, a)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._video_progress(dur)

    def _x265(self, i, o, x, d, q, p, t, c, a):
        print('Encode video...')
        self._update_queue()
        dur = self._info(i)
        cmd = command.x265(i, o, x, d, q, p, t, c, a)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._video_progress(dur)

    def _faac(self, i, o, t, r, c, m, b, q, co):
        print('Encode audio...')
        self._update_queue()
        cmd = command.faac(i, o, t, r, c, m, b, q, co)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libfaac(self, i, o, t, r, c, m, b, q, co):
        print('Encode audio...')
        self._update_queue()
        cmd = command.ffmpeg_libfaac(i, o, t, r, c, m, b, q, co)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _fdkaac(self, i, o, t, r, c, m, b, q, co):
        print('Encode audio...')
        self._update_queue()
        cmd = command.fdkaac(i, o, t, r, c, m, b, q, co)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libfdk_aac(self, i, o, t, r, c, m, b, q, co):
        print('Encode audio...')
        self._update_queue()
        cmd = command.ffmpeg_libfdk_aac(i, o, t, r, c, m, b, q, co)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _flac(self, i, o, t, r, c, cp, co):
        print('Encode audio...')
        self._update_queue()
        cmd = command.flac(i, o, t, r, c, cp, co)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _native_flac(self, i, o, t, r, c, cp, co):
        print('Encode audio...')
        self._update_queue()
        cmd = command.ffmpeg_flac(i, o, t, r, c, cp, co)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _lame(self, i, o, t, r, c, m, b, q, co):
        print('Encode audio...')
        self._update_queue()
        cmd = command.lame(i, o, t, r, c, m, b, q, co)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libmp3lame(self, i, o, t, r, c, m, b, q, co):
        print('Encode audio...')
        self._update_queue()
        cmd = command.ffmpeg_libmp3lame(i, o, t, r, c, m, b, q, co)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _opusenc(self, i, o, t, r, c, m, b, co):
        print('Encode audio...')
        self._update_queue()
        cmd = command.opusenc(i, o, t, r, c, m, b, co)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libopus(self, i, o, t, r, c, m, b, co):
        print('Encode audio...')
        self._update_queue()
        cmd = command.ffmpeg_libopus(i, o, t, r, c, m, b, co)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _oggenc(self, i, o, t, r, c, m, b, q, co):
        print('Encode audio...')
        self._update_queue()
        cmd = command.oggenc(i, o, t, r, c, m, b, q, co)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libvorbis(self, i, o, t, r, c, m, b, q, co):
        print('Encode audio...')
        self._update_queue()
        cmd = command.ffmpeg_libvorbis(i, o, t, r, c, m, b, q, co)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _mkvtoolnix_progress(self, mode):
        GLib.idle_add(self.pbar.set_fraction, 0)
        if mode == 'x':
            GLib.idle_add(self.pbar.set_text, 'Extracting tracks...')
        elif mode == 'm':
            GLib.idle_add(self.pbar.set_text, 'Merging tracks...')
        while self.proc.poll() == None:
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
        while self.proc.poll() == None:
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
        while self.proc.poll() == None:
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

class AboutDialog(Gtk.AboutDialog):

    def __init__(self, parent):
        Gtk.Dialog.__init__(self, parent)
        self.set_property('program-name', 'pyanimenc')
        self.set_property('version', VERSION)
        self.set_property('comments', 'Python Transcoding Tools')
        self.set_property('copyright', 'Copyright © 2014-2015 Maxime Gauduin')
        self.set_property('license-type', Gtk.License.GPL_3_0)
        self.set_property('website', 'https://github.com/alucryd/pyanimenc')

win = MainWindow()
win.connect('delete-event', Gtk.main_quit)

win.show_all()

Gtk.main()

# vim: ts=4 sw=4 et:
