#!/usr/bin/env python3

import copy
import os

import pyhenkan.conf as conf
from pyhenkan.chapter import ChapterEditorWindow
from pyhenkan.encoders import EncoderDialog
from pyhenkan.mediafile import MediaFile
from pyhenkan.queue import Queue
from pyhenkan.script import ScriptCreatorWindow
from pyhenkan.vapoursynth import VapourSynthDialog

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import GdkPixbuf, Gio, Gtk, Notify

VERSION = '0.1.0'
AUTHOR = 'Maxime Gauduin <alucryd@gmail.com>'


class MainWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='pyhenkan')
        self.set_default_size(800, 600)

        self.connect('delete-event', self.on_delete_event)

        # Set default working directory
        self.wdir = os.environ['HOME']

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
        hbar.set_property('title', 'pyhenkan')
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

        for f in self.files:
            t = f.tracklist[int(path)]

            if i == 0:
                t.enable = v
            elif i == 2:
                t.encode = v

        self.track_lstore[path][i] = v

    def on_cell_edited(self, crtext, path, v, i):
        for f in self.files:
            t = f.tracklist[int(path)]

            if i == 6:
                t.title = v
            elif i == 7:
                # Language is a 3 letter code
                # TODO: write a custom cell renderer for this
                v = v[:3]
                t.lang = v

        self.track_lstore[path][i] = v

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
            self.files = []
            self.track_lstore.clear()

            self.wdir = dlg.get_current_folder()
            for f in dlg.get_filenames():
                self.files.append(MediaFile(f))

            if len(self.files) > 1:
                self.out_name_entry.set_text('')
                self.out_name_entry.set_sensitive(False)
            else:
                # Get the filename without extension
                self.out_name_entry.set_text(self.files[0].name)
                self.out_name_entry.set_sensitive(True)

            if len(self.files) == 1 or self._check_consistency():
                self._populate_lstore()
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

    def _populate_lstore(self):
        for t in self.files[0].tracklist:
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
        for f in self.files:
            name = self.out_name_entry.get_text()
            if name:
                f.oname = name
            suffix = self.out_suffix_entry.get_text()
            if suffix:
                f.osuffix = suffix
            cont = self.out_cont_cbtext.get_active_text()
            f.ocont = cont

            for t in f.tracklist:
                if t.type == 'Video' and t.enable and t.encode:
                    k = self.venc_cbtext.get_active_text()
                    x = conf.VENCS[k]
                    t.codec = x
                    # This needs a deep copy
                    t.filters = copy.deepcopy(conf.filters)
                elif t.type == 'Audio' and t.enable and t.encode:
                    k = self.aenc_cbtext.get_active_text()
                    x = conf.AENCS[k]
                    t.codec = x
                    t.filters = [conf.audio['rate'], conf.audio['channel'],
                                 conf.video['fpsnum'], conf.video['fpsden'],
                                 conf.trim]

            f.process(self.pbar)

            # Clean up
            self.queue.worker.submit(f.clean, self.pbar)

            # Update queue
            self.queue.worker.submit(self.queue.update)

            # Add a wait job after each encoding job
            future = self.queue.worker.submit(self.queue.wait)
            self.queue.waitlist.append(future)

            if self.queue.idle:
                self.queue_start_button.set_sensitive(True)
                self.queue_del_button.set_sensitive(True)
                self.queue_clr_button.set_sensitive(True)

            # Create new MediaFile instances
                for i in range(len(self.files)):
                    f = self.files[i]
                    self.files[i] = MediaFile(f.path)

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
        while self.proc.poll() is None:
            self.proc.terminate()

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

        self.pbar.set_fraction(0)
        self.pbar.set_text('Ready')
        self.queue_stop_button.set_sensitive(False)
        self.queue_clr_button.set_sensitive(True)

    def on_del_clicked(self, button):
        job = self.queue_tselection.get_selected()[1]
        # If child, select parent instead
        if self.queue.store.iter_depth(job) == 1:
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
            idx = self.queue.store.get_path(job).get_indices()[0]
            self.waitlist[idx].cancel()
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
            for future in self.waitlist:
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
