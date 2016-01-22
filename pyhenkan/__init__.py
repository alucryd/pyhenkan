#!/usr/bin/env python3

import os

from collections import OrderedDict

import pyhenkan.codec as codec
from pyhenkan.chapter import ChapterEditorWindow
from pyhenkan.mediafile import MediaFile
from pyhenkan.queue import Queue
from pyhenkan.script import ScriptCreatorWindow
from pyhenkan.vapoursynth import VapourSynth

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import GdkPixbuf, Gio, Gtk, Notify

VERSION = '0.1.0'
AUTHOR = 'Maxime Gauduin <alucryd@gmail.com>'


class MainWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='pyhenkan')
        self.set_default_size(640, 480)

        self.connect('delete-event', self.on_delete_event)

        # Set default working directory
        self.wdir = os.environ['HOME']

        # --File Filters--#
        self.vconts = ['mkv']

        self.sflt = Gtk.FileFilter()
        self.sflt.set_name('VapourSynth scripts')
        self.sflt.add_pattern('*.vpy')

        vext = ['3gp', 'avi', 'flv', 'm2ts', 'mkv', 'mp4', 'ogm', 'webm']
        self.vflt = Gtk.FileFilter()
        self.vflt.set_name('Video files')
        for ext in vext:
            self.vflt.add_pattern('*.' + ext)

        aext = ['aac', 'ac3', 'dts', 'flac', 'm4a', 'mka', 'mp3', 'mpc', 'ogg',
                'opus', 'thd', 'wav', 'wv']
        self.aflt = Gtk.FileFilter()
        self.aflt.set_name('Audio files')
        for ext in aext:
            self.aflt.add_pattern('*.' + ext)

        # -- Header Bar -- #
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
        hbar.set_property('title', 'pyhenkan')
        hbar.pack_start(open_button)
        hbar.pack_start(tools_mbutton)
        hbar.pack_end(about_button)

        self.set_titlebar(hbar)

        # -- Input -- #
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
        self.out_suffix_entry.set_width_chars(5)
        self.out_suffix_entry.set_max_width_chars(5)
        self.out_suffix_entry.set_text('new')

        self.out_cont_cbtext = Gtk.ComboBoxText()
        self.out_cont_cbtext.set_property('hexpand', True)
        for cont in self.vconts:
            self.out_cont_cbtext.append_text(cont)
        self.out_cont_cbtext.set_active(0)

        vsep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        hsep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

        self.flt_conf_button = Gtk.Button('Filters')
        self.flt_conf_button.set_sensitive(False)
        self.flt_conf_button.connect('clicked', self.on_filters_clicked)

        self.queue_button = Gtk.Button('Queue')
        self.queue_button.set_property('hexpand', True)
        self.queue_button.set_sensitive(False)
        self.queue_button.connect('clicked', self.on_queue_clicked)

        grid = Gtk.Grid()
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        grid.attach(fname_label, 0, 0, 1, 1)
        grid.attach(self.out_name_entry, 0, 1, 1, 1)
        grid.attach(out_uscore_label, 1, 1, 1, 1)
        grid.attach(suffix_label, 2, 0, 1, 1)
        grid.attach(self.out_suffix_entry, 2, 1, 1, 1)
        grid.attach(out_dot_label, 3, 1, 1, 1)
        grid.attach(cont_label, 4, 0, 1, 1)
        grid.attach(self.out_cont_cbtext, 4, 1, 1, 1)
        grid.attach(vsep, 5, 0, 1, 2)
        grid.attach(self.flt_conf_button, 6, 0, 1, 1)
        grid.attach(self.queue_button, 6, 1, 1, 1)
        grid.attach(hsep, 0, 3, 7, 1)

        tracks_empty_label = Gtk.Label('No input')
        tracks_empty_label.set_property('hexpand', True)
        tracks_empty_label.set_property('vexpand', True)

        self.tracks_grid = Gtk.Grid()
        self.tracks_grid.set_column_spacing(6)
        self.tracks_grid.set_row_spacing(6)
        self.tracks_grid.attach(tracks_empty_label, 0, 0, 1, 1)

        self.tracks_scrwin = Gtk.ScrolledWindow()
        self.tracks_scrwin.set_policy(Gtk.PolicyType.NEVER,
                                      Gtk.PolicyType.ALWAYS)
        self.tracks_scrwin.add(self.tracks_grid)

        # -- Queue -- #
        self.queue = Queue()

        qexp_crpixbuf = Gtk.CellRendererPixbuf()
        qexp_crpixbuf.set_property('is-expander', True)
        qexp_tvcolumn = Gtk.TreeViewColumn('', qexp_crpixbuf)

        qin_crtext = Gtk.CellRendererText()
        qin_tvcolumn = Gtk.TreeViewColumn('Input', qin_crtext, text=1)

        qcod_crtext = Gtk.CellRendererText()
        qcod_tvcolumn = Gtk.TreeViewColumn('Codec', qcod_crtext, text=2)

        qsta_crtext = Gtk.CellRendererText()
        qsta_tvcolumn = Gtk.TreeViewColumn('Status', qsta_crtext, text=3)

        queue_tview = Gtk.TreeView(self.queue.tstore)
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

        # -- Notebook --#
        input_label = Gtk.Label('Input')
        queue_label = Gtk.Label('Queue')

        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        input_box.set_property('margin', 6)
        input_box.pack_start(grid, False, False, 0)
        input_box.pack_start(self.tracks_scrwin, True, True, 0)

        queue_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        queue_box.set_property('margin', 6)
        queue_box.pack_start(queue_scrwin, True, True, 0)
        queue_box.pack_start(queue_ctl_box, False, True, 0)

        notebook = Gtk.Notebook()
        notebook.append_page(input_box, input_label)
        notebook.append_page(queue_box, queue_label)

        for tab in notebook.get_children():
            notebook.child_set_property(tab, 'tab-expand', True)

        # -- Main Box -- #
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.pack_start(notebook, True, True, 0)
        main_box.pack_start(self.queue.pbar, False, True, 0)

        self.add(main_box)

        # -- About Dialog -- #
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

    def on_open_clicked(self, button):
        dlg = Gtk.FileChooserDialog('Select File(s)', self,
                                    Gtk.FileChooserAction.OPEN,
                                    ('Cancel',
                                     Gtk.ResponseType.CANCEL,
                                     'Open', Gtk.ResponseType.OK))
        dlg.set_property('select-multiple', True)
        dlg.add_filter(self.vflt)
        dlg.set_current_folder(self.wdir)

        response = dlg.run()

        if response == Gtk.ResponseType.OK:
            self.files = []

            self.wdir = dlg.get_current_folder()
            for f in dlg.get_filenames():
                self.files.append(MediaFile(f))

            # TODO find a cleaner way to do this
            self.workfile = self.files[0]
            self.tracklist = self.workfile.tracklist
            # We want these to be edited globally
            for f in self.files:
                f.filters = self.workfile.filters
                f.width = self.workfile.width
                f.height = self.workfile.height
                f.fpsnum = self.workfile.fpsnum
                f.fpsden = self.workfile.fpsden
                f.first = self.workfile.first
                f.last = self.workfile.last

            if len(self.files) > 1:
                self.out_name_entry.set_text('')
                self.out_name_entry.set_sensitive(False)
            else:
                # Get the filename without extension
                self.out_name_entry.set_text(self.files[0].name)
                self.out_name_entry.set_sensitive(True)

            isconsistent = self._check_consistency()

            if len(self.files) == 1 or isconsistent:
                self._populate_tracklist()
                self.flt_conf_button.set_sensitive(True)
                self.queue_button.set_sensitive(True)

        dlg.destroy()

    def _check_consistency(self):
        # Make sure tracks are identical across files
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO,
                                   Gtk.ButtonsType.OK, 'Track Mismatch')

        f_ref = self.files[0]
        t_ref = f_ref.tracklist

        for f in self.files:
            m = f.compare(f_ref)
            if m:
                dialog.format_secondary_text(m)
                dialog.run()
                dialog.destroy()

                return False

            for i in range(len(f.tracklist)):
                t = f.tracklist[i]
                t_ref = f_ref.tracklist[i]
                m = t.compare(t_ref)
                if m:
                    dialog.format_secondary_text(m)
                    dialog.run()
                    dialog.destroy()

                    return False

        dialog.destroy()

        return True

    def _populate_tracklist(self):
        for child in self.tracks_grid.get_children():
            self.tracks_grid.remove(child)

        type_label = Gtk.Label('Type')
        format_label = Gtk.Label('Format')
        title_label = Gtk.Label('Title')
        title_label.set_property('hexpand', True)
        lang_label = Gtk.Label('Language')
        codec_label = Gtk.Label('Codec')

        self.tracks_grid.attach(type_label, 0, 0, 1, 1)
        self.tracks_grid.attach(format_label, 1, 0, 1, 1)
        self.tracks_grid.attach(title_label, 2, 0, 1, 1)
        self.tracks_grid.attach(lang_label, 3, 0, 1, 1)
        self.tracks_grid.attach(codec_label, 4, 0, 1, 1)

        for i in range(len(self.tracklist)):
            t = self.tracklist[i]
            edit = False if t.type == 'Menu' else True

            type_label = Gtk.Label(t.type)

            format_label = Gtk.Label(t.format)

            title_entry = Gtk.Entry()
            title_entry.set_property('hexpand', True)
            title_entry.set_text(t.title)
            title_entry.set_sensitive(edit)
            title_entry.connect('changed', self.on_title_changed, i)

            lang_entry = Gtk.Entry()
            lang_entry.set_max_length(3)
            lang_entry.set_width_chars(3)
            lang_entry.set_max_width_chars(3)
            lang_entry.set_text(t.lang)
            lang_entry.set_sensitive(edit)
            lang_entry.connect('changed', self.on_lang_changed, i)

            codec_cbtext = Gtk.ComboBoxText()
            codec_cbtext.append_text('Disable')
            codec_cbtext.append_text('Mux')
            if t.type == 'Video':
                self._populate_vcodecs()
                for c in self.vcodecs:
                    codec_cbtext.append_text(c)
            elif t.type == 'Audio':
                self._populate_acodecs()
                for c in self.acodecs:
                    codec_cbtext.append_text(c)
            codec_cbtext.set_active(1)
            codec_cbtext.connect('changed', self.on_codec_changed, i)

            conf_icon = Gio.ThemedIcon(name='applications-system-symbolic')
            conf_image = Gtk.Image.new_from_gicon(conf_icon,
                                                  Gtk.IconSize.BUTTON)
            conf_button = Gtk.Button()
            conf_button.set_image(conf_image)
            conf_button.connect('clicked', self.on_conf_clicked, i)
            if t.type in ['Text', 'Menu']:
                conf_button.set_sensitive(False)

            codec_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                 spacing=6)
            codec_hbox.pack_start(codec_cbtext, True, True, 0)
            codec_hbox.pack_start(conf_button, False, True, 0)

            self.tracks_grid.attach(type_label, 0, i + 1, 1, 1)
            self.tracks_grid.attach(format_label, 1, i + 1, 1, 1)
            self.tracks_grid.attach(title_entry, 2, i + 1, 1, 1)
            self.tracks_grid.attach(lang_entry, 3, i + 1, 1, 1)
            self.tracks_grid.attach(codec_hbox, 4, i + 1, 1, 1)

        self.tracks_grid.show_all()

    def _populate_vcodecs(self):
        self.vcodecs = OrderedDict()
        self.vcodecs['VP8 (libvpx)'] = codec.Vp8()
        self.vcodecs['VP9 (libvpx)'] = codec.Vp9()
        self.vcodecs['AVC (libx264)'] = codec.X264()
        self.vcodecs['HEVC (libx265)'] = codec.X265()

        not_found = []
        for c in self.vcodecs:
            if not self.vcodecs[c].is_avail():
                not_found.append(c)

        for c in not_found:
            self.vcodecs.pop(c)

    def _populate_acodecs(self):
        self.acodecs = OrderedDict()
        self.acodecs['AAC (native)'] = codec.Aac()
        self.acodecs['AAC (libfaac)'] = codec.Faac()
        self.acodecs['AAC (libfdk-aac)'] = codec.Fdkaac()
        self.acodecs['FLAC (native)'] = codec.Flac()
        self.acodecs['MP3 (libmp3lame)'] = codec.Lame()
        self.acodecs['Opus (libopus)'] = codec.Opus()
        self.acodecs['Vorbis (libvorbis)'] = codec.Vorbis()

        not_found = []
        for c in self.acodecs:
            if not self.acodecs[c].is_avail():
                not_found.append(c)

        for c in not_found:
            self.acodecs.pop(c)

    def on_title_changed(self, entry, i):
        title = entry.get_text()
        for f in self.files:
            f.tracklist[i].title = title

    def on_lang_changed(self, entry, i):
        lang = entry.get_text()
        for f in self.files:
            f.tracklist[i].lang = lang

    def on_codec_changed(self, cbtext, i):
        c = cbtext.get_active_text()
        for f in self.files:
            t = f.tracklist[i]
            if c == 'Disable':
                t.enable = False
                t.codec = None
            elif c == 'Mux':
                t.enable = True
                t.codec = None
            else:
                t.enable = True
                if t.type == 'Video':
                    t.codec = self.vcodecs[c]
                elif t.type == 'Audio':
                    t.codec = self.acodecs[c]
                    t.codec.channel = t.channel
                    t.codec.rate = t.rate

    def on_filters_clicked(self, button):
        VapourSynth(self.workfile).show_dialog(self)

    def on_conf_clicked(self, button, i):
        if self.workfile.tracklist[i].codec:
            self.workfile.tracklist[i].codec.show_dialog(self)

    def on_queue_clicked(self, button):
        for f in self.files:
            name = self.out_name_entry.get_text()
            if name:
                f.oname = name
            suffix = self.out_suffix_entry.get_text()
            if suffix:
                f.osuffix = suffix
            cont = self.out_cont_cbtext.get_active_text()
            f.ocont = cont

            f.process()

            # Clean up
            self.queue.executor.submit(f.clean)

            # Update queue
            self.queue.executor.submit(self.queue.update)

            # Add a wait job after each encoding job
            future = self.queue.executor.submit(self.queue.wait)
            self.queue.waitlist.append(future)
            if self.queue.idle:
                self.queue_start_button.set_sensitive(True)
                self.queue_del_button.set_sensitive(True)
                self.queue_clr_button.set_sensitive(True)

            # Create new MediaFile instances and carry settings over
            # Otherwise they may have changed by the time jobs are processed
                for i in range(len(self.files)):
                    self.files[i] = self.files[i].copy()
                self.workfile = self.files[0]
                self.tracklist = self.workfile.tracklist

    def on_start_clicked(self, button):
        if len(self.queue.tstore):
            self.queue_stop_button.set_sensitive(True)
            self.queue_del_button.set_sensitive(False)
            self.queue_clr_button.set_sensitive(False)
            print('Start processing...')
            self.queue.idle = False
            self.queue.lock.release()

    def on_stop_clicked(self, button):
        self.idle = True
        print('Stop processing...')
        # Wait for the process to terminate
        while self.queue.proc.poll() is None:
            self.queue.proc.terminate()

        for job in self.queue.tstore:
            status = self.queue.tstore.get_value(job.iter, 3)
            if status == 'Running':
                for step in job.iterchildren():
                    future = self.queue.tstore.get_value(step.iter, 0)
                    # Cancel and mark steps as failed
                    if not future.done():
                        self.queue.tstore.set_value(step.iter, 3, 'Failed')
                        future.cancel()
                # Mark job as failed
                self.queue.tstore.set_value(job.iter, 3, 'Failed')

        self.queue.pbar.set_fraction(0)
        self.queue.pbar.set_text('Ready')
        self.queue_stop_button.set_sensitive(False)
        self.queue_clr_button.set_sensitive(True)

    def on_del_clicked(self, button):
        job = self.queue_tselection.get_selected()[1]
        # If child, select parent instead
        if self.queue.tstore.iter_depth(job) == 1:
            job = self.queue.tstore.iter_parent(job)
        status = self.queue.tstore.get_value(job, 3)
        while self.queue.tstore.iter_has_child(job):
            step = self.queue.tstore.iter_nth_child(job, 0)
            future = self.queue.tstore.get_value(step, 0)
            # Cancel pending step
            if not future.done():
                future.cancel()
            self.queue.tstore.remove(step)
        # Cancel associated wait job
        if status not in ['Done', 'Failed']:
            i = self.queue.tstore.get_path(job).get_indices()[0]
            self.queue.waitlist[i].cancel()
        # Delete job
        self.queue.tstore.remove(job)

        if not len(self.queue.tstore):
            self.queue_start_button.set_sensitive(False)
            self.queue_del_button.set_sensitive(False)
            self.queue_clr_button.set_sensitive(False)

    def on_clr_clicked(self, button):
        for job in self.queue.tstore:
            # Cancel jobs before clearing them
            for step in job.iterchildren():
                future = self.queue.tstore.get_value(step.iter, 0)
                future.cancel()
            for future in self.queue.waitlist:
                future.cancel()
        # Clear queue
        self.queue.tstore.clear()

        self.queue_start_button.set_sensitive(False)
        self.queue_del_button.set_sensitive(False)
        self.queue_clr_button.set_sensitive(False)

    def on_delete_event(event, self, widget):
        # Cancel all jobs
        for job in self.queue.tstore:
            for step in job.iterchildren():
                future = self.queue.tstore.get_value(step.iter, 0)
                if not future.done():
                    future.cancel()
        for future in self.queue.waitlist:
            future.cancel()
        Notify.uninit()
        self.queue.lock.release()
        Gtk.main_quit()


class AboutDialog(Gtk.AboutDialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, parent)

        pixbuf = GdkPixbuf.Pixbuf
        logo = pixbuf.new_from_file('/usr/share/pixmaps/pyhenkan.png')
        logo = logo.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)

        self.set_program_name('pyhenkan')
        self.set_logo(logo)
        self.set_version(VERSION)
        self.set_comments('Python Transcoding Tools')
        self.set_copyright('Copyright © 2014-2015 Maxime Gauduin')
        self.set_license_type(Gtk.License.GPL_3_0)
        self.set_website('https://github.com/alucryd/pyhenkan')

MainWindow().show_all()
Gtk.main()

# vim: ts=4 sw=4 et:
