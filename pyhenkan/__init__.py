#!/usr/bin/env python3

import os

from pyhenkan.chapter import ChapterEditorWindow
from pyhenkan.environment import Environment
from pyhenkan.mediafile import MediaFile
from pyhenkan.plugin import CropAbs, CropRel, ResizePlugin, SourcePlugin
from pyhenkan.queue import Queue
from pyhenkan.script import ScriptCreatorWindow
from pyhenkan.vapoursynth import VapourSynth

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import GdkPixbuf, Gio, GLib, Gtk, Notify

VERSION = '0.1.0'
AUTHOR = 'Maxime Gauduin <alucryd@gmail.com>'


class MainWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='pyhenkan')
        self.set_default_size(640, 0)

        self.connect('delete-event', self.on_delete_event)

        # Set default working directory
        self.wdir = os.environ['HOME']

        # Get environment
        self.env = Environment()

        # --File Filters--#
        self.vconts = ['mkv']

        self.sflt = Gtk.FileFilter()
        self.sflt.set_name('VapourSynth scripts')
        self.sflt.add_pattern('*.vpy')

        vext = ['3gp', 'avi', 'flv', 'm2ts', 'mkv', 'mp4', 'ogm', 'ts', 'webm']
        self.vflt = Gtk.FileFilter()
        self.vflt.set_name('Video files')
        for ext in vext:
            self.vflt.add_pattern('*.' + ext)

        aext = ['aac', 'ac3', 'dts', 'flac', 'm4a', 'mka', 'mp3', 'mpc', 'ogg', 'opus', 'thd', 'wav', 'wv']
        self.aflt = Gtk.FileFilter()
        self.aflt.set_name('Audio files')
        for ext in aext:
            self.aflt.add_pattern('*.' + ext)

        self.noflt = Gtk.FileFilter()
        self.noflt.set_name("All files")
        self.noflt.add_pattern("*")

        # -- Header Bar -- #
        tools_sccr_button = Gtk.Button()
        tools_sccr_button.set_label('Script Creator')
        tools_sccr_button.connect('clicked', self.on_sccr_clicked)

        tools_ched_button = Gtk.Button()
        tools_ched_button.set_label('Chapter Editor')
        tools_ched_button.connect('clicked', self.on_ched_clicked)

        tools_env_button = Gtk.Button()
        tools_env_button.set_label('Environment')
        tools_env_button.connect('clicked', self.on_env_clicked)

        tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        tools_box.set_property('margin', 6)
        tools_box.pack_start(tools_sccr_button, True, True, 0)
        tools_box.pack_start(tools_ched_button, True, True, 0)
        tools_box.pack_start(tools_env_button, True, True, 0)
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

        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.set_property('title', 'pyhenkan')
        hbar.pack_start(tools_mbutton)
        hbar.pack_end(about_button)

        self.set_titlebar(hbar)

        # -- Input -- #
        select_button = Gtk.Button()
        select_button.set_label('Select File(s)')
        select_button.connect('clicked', self.on_select_clicked)

        input_hsep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

        self.input_grid = Gtk.Grid()
        self.input_grid.set_column_spacing(6)
        self.input_grid.set_row_spacing(6)

        self.input_scrwin = Gtk.ScrolledWindow()
        self.input_scrwin.set_policy(Gtk.PolicyType.NEVER,
                                     Gtk.PolicyType.AUTOMATIC)
        self.input_scrwin.add(self.input_grid)

        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        input_box.set_property('margin', 6)
        input_box.pack_start(select_button, False, False, 0)
        input_box.pack_start(input_hsep, False, False, 0)
        input_box.pack_start(self.input_scrwin, True, True, 0)

        # -- Output -- #
        output_hsep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        output_hsep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        output_hsep3 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

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

        self.filters_button = Gtk.Button('VapourSynth Filters')
        self.filters_button.set_sensitive(False)
        self.filters_button.connect('clicked', self.on_filters_clicked)

        self.dimensions_label = Gtk.Label('Dimensions: Unknown')
        self.fps_label = Gtk.Label('FPS: Unknown')
        trim_label = Gtk.Label('Trim')

        start_adj = Gtk.Adjustment(0, 0, 512000, 1, 10)
        end_adj = Gtk.Adjustment(0, 0, 512000, 1, 10)

        self.out_start_spin = Gtk.SpinButton()
        self.out_start_spin.set_adjustment(start_adj)
        self.out_start_spin.set_numeric(True)
        self.out_start_spin.set_property('hexpand', True)
        self.out_start_spin.connect('value_changed', self.on_trim_changed, 0)

        self.out_end_spin = Gtk.SpinButton()
        self.out_end_spin.set_adjustment(end_adj)
        self.out_end_spin.set_numeric(True)
        self.out_end_spin.set_property('hexpand', True)
        self.out_end_spin.connect('value_changed', self.on_trim_changed, 1)

        output_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                              spacing=6)
        output_hbox.pack_start(self.out_name_entry, True, True, 0)
        output_hbox.pack_start(Gtk.Label('_'), False, False, 0)
        output_hbox.pack_start(self.out_suffix_entry, True, True, 0)
        output_hbox.pack_start(Gtk.Label('.'), False, False, 0)
        output_hbox.pack_start(self.out_cont_cbtext, False, True, 0)

        self.queue_button = Gtk.Button('Queue')
        self.queue_button.set_property('hexpand', True)
        self.queue_button.set_sensitive(False)
        self.queue_button.connect('clicked', self.on_queue_clicked)

        output_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                             spacing=6)
        output_box.set_property('margin', 6)
        output_box.pack_start(output_hbox, True, True, 0)
        output_box.pack_start(output_hsep1, False, False, 0)
        output_box.pack_start(self.filters_button, True, True, 0)
        output_box.pack_start(self.dimensions_label, True, True, 0)
        output_box.pack_start(self.fps_label, True, True, 0)
        output_box.pack_start(output_hsep2, False, False, 0)
        output_box.pack_start(trim_label, True, True, 0)
        output_box.pack_start(self.out_start_spin, True, True, 0)
        output_box.pack_start(self.out_end_spin, True, True, 0)
        output_box.pack_start(output_hsep3, False, False, 0)
        output_box.pack_start(self.queue_button, False, False, 0)

        # -- Queue -- #
        self.queue = Queue()

        # -- Notebook --#
        input_label = Gtk.Label('Input')
        output_label = Gtk.Label('Output')
        queue_label = Gtk.Label('Queue')

        notebook = Gtk.Notebook()
        notebook.append_page(input_box, input_label)
        notebook.append_page(output_box, output_label)
        notebook.append_page(self.queue.vbox, queue_label)

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

    def on_env_clicked(self, button):
        self.env.show_window(self)

    def on_about_clicked(self, button):
        self.about_dlg.run()
        self.about_dlg.hide()

    def on_select_clicked(self, button):
        dlg = Gtk.FileChooserDialog('Select File(s)', self,
                                    Gtk.FileChooserAction.OPEN,
                                    ('Cancel',
                                     Gtk.ResponseType.CANCEL,
                                     'Open', Gtk.ResponseType.OK))
        dlg.set_property('select-multiple', True)
        dlg.add_filter(self.vflt)
        dlg.add_filter(self.noflt)
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
                f.dimensions = self.workfile.dimensions
                f.fps = self.workfile.fps
                f.trim = self.workfile.trim

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
                self.filters_button.set_sensitive(True)
                self.queue_button.set_sensitive(True)
                self._update_summary()

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
        for child in self.input_grid.get_children():
            self.input_grid.remove(child)

        type_label = Gtk.Label('Type')
        format_label = Gtk.Label('Format')
        title_label = Gtk.Label('Title')
        title_label.set_property('hexpand', True)
        lang_label = Gtk.Label('Language')
        codec_label = Gtk.Label('Codec')
        default_label = Gtk.Label('Default')

        hsep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

        self.input_grid.attach(type_label, 0, 0, 1, 1)
        self.input_grid.attach(format_label, 2, 0, 1, 1)
        self.input_grid.attach(title_label, 4, 0, 1, 1)
        self.input_grid.attach(lang_label, 6, 0, 1, 1)
        self.input_grid.attach(codec_label, 8, 0, 1, 1)
        self.input_grid.attach(default_label, 10, 0, 1, 1)
        self.input_grid.attach(hsep, 0, 1, 11, 1)

        # Dummy radios to serve as groups
        video_radio = Gtk.RadioButton()
        audio_radio = Gtk.RadioButton()
        text_radio = Gtk.RadioButton()

        i = 0
        for t in self.tracklist:
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
                for c in self.env.vencs:
                    if self.env.vencs[c][1]:
                        codec_cbtext.append_text(c)
            elif t.type == 'Audio':
                for c in self.env.aencs:
                    if self.env.aencs[c][1]:
                        codec_cbtext.append_text(c)
            codec_cbtext.set_active(1)
            codec_cbtext.connect('changed', self.on_codec_changed, i)

            conf_icon = Gio.ThemedIcon(name='applications-system-symbolic')
            conf_image = Gtk.Image.new_from_gicon(conf_icon,
                                                  Gtk.IconSize.BUTTON)
            conf_button = Gtk.Button()
            conf_button.set_image(conf_image)
            conf_button.set_sensitive(False)
            conf_button.connect('clicked', self.on_conf_clicked, i)

            codec_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                 spacing=6)
            codec_hbox.pack_start(codec_cbtext, True, True, 0)
            codec_hbox.pack_start(conf_button, False, True, 0)

            if t.type == 'Video':
                default_radio = Gtk.RadioButton.new_from_widget(video_radio)
            elif t.type == 'Audio':
                default_radio = Gtk.RadioButton.new_from_widget(audio_radio)
            elif t.type == 'Text':
                default_radio = Gtk.RadioButton.new_from_widget(text_radio)
            default_radio.set_active(t.default)
            default_radio.connect('toggled', self.on_default_toggled, i)

            self.input_grid.attach(type_label, 0, i + 2, 1, 1)
            self.input_grid.attach(format_label, 2, i + 2, 1, 1)
            self.input_grid.attach(title_entry, 4, i + 2, 1, 1)
            self.input_grid.attach(lang_entry, 6, i + 2, 1, 1)
            self.input_grid.attach(codec_hbox, 8, i + 2, 1, 1)
            self.input_grid.attach(default_radio, 10, i + 2, 1, 1)

            i += 1

        for j in range(5):
            vsep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            self.input_grid.attach(vsep, j * 2 + 1, 0, 1, i + 3)

        self.input_grid.show_all()

    def _update_summary(self):
        f = self.workfile
        f.dimensions[0:2] = f.dimensions[2:5]
        f.fps[0:2] = f.fps[2:5]

        for flt in self.workfile.filters:
            if isinstance(flt, SourcePlugin) and flt.args['fpsnum'] > 0:
                f.fps[0:2] = [flt.args['fpsnum'], flt.args['fpsden']]
            elif isinstance(flt, ResizePlugin) or isinstance(flt, CropAbs):
                f.dimensions[0:2] = [flt.args['width'], flt.args['height']]
            elif isinstance(flt, CropRel):
                f.dimensions[0] -= flt.args['right'] + flt.args['left']
                f.dimensions[1] -= flt.args['top'] + flt.args['bottom']

        self.dimensions_label.set_text('Dimensions: ' +
                                       str(f.dimensions[0]) +
                                       'x' +
                                       str(f.dimensions[1]))
        if f.fps[0:2] != [0, 1]:
            self.fps_label.set_text('FPS: ' +
                                    str(f.fps[0]) +
                                    '/' +
                                    str(f.fps[1]))
        else:
            self.fps_label.set_text('FPS: VFR')

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
        conf_button = self.input_grid.get_child_at(8, i + 2).get_children()[1]
        for f in self.files:
            t = f.tracklist[i]
            if c in ['Disable', 'Mux']:
                conf_button.set_sensitive(False)
            if c == 'Disable':
                t.enable = False
                t.codec = None
            elif c == 'Mux':
                t.enable = True
                t.codec = None
            else:
                conf_button.set_sensitive(True)
                t.enable = True
                if t.type == 'Video':
                    t.codec = self.env.vencs[c][0]()
                elif t.type == 'Audio':
                    t.codec = self.env.aencs[c][0]()
                    t.codec.channel = t.channel
                    t.codec.rate = t.rate

    def on_trim_changed(self, spin, i):
        self.workfile.trim[i] = spin.get_value_as_int()

    def on_filters_clicked(self, button):
        VapourSynth(self.workfile).show_dialog(self)
        self._update_summary()

    def on_conf_clicked(self, button, i):
        if self.workfile.tracklist[i].codec:
            self.workfile.tracklist[i].codec.show_dialog(self)

    def on_default_toggled(self, button, i):
        default = button.get_active()
        for f in self.files:
            f.tracklist[i].default = default

        # # Only one default track per type
        # if state:
        #     for t in tracklist:
        #         if tracklist.index(t) != i and t.type == track.type:
        #             t.default = False

    def on_queue_clicked(self, button):
        for f in self.files:
            name = self.out_name_entry.get_text()
            suffix = self.out_suffix_entry.get_text()
            cont = self.out_cont_cbtext.get_active_text()
            f.oname = '.'.join(['_'.join([name if name else f.name, suffix]),
                                cont])

            f.process()

            # Clean up
            self.queue.executor.submit(f.clean)

            # Update queue
            self.queue.executor.submit(self.queue.update)

            # Add a wait job after each encoding job
            future = self.queue.executor.submit(self.queue.wait)
            self.queue.waitlist.append(future)
            if self.queue.idle:
                GLib.idle_add(self.queue.start_button.set_sensitive, True)
                GLib.idle_add(self.queue.delete_button.set_sensitive, True)
                GLib.idle_add(self.queue.clear_button.set_sensitive, True)

            # Create new MediaFile instances and carry settings over
            # Otherwise they may have changed by the time jobs are processed
                for i in range(len(self.files)):
                    self.files[i] = self.files[i].copy()
                self.workfile = self.files[0]
                self.tracklist = self.workfile.tracklist

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
        logo = pixbuf.new_from_file('/usr/share/pixmaps/pyhenkan.svg')
        logo = logo.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)
        comments = 'Transcoding suite built around VapourSynth and FFmpeg'

        self.set_program_name('pyhenkan')
        self.set_logo(logo)
        self.set_version(VERSION)
        self.set_comments(comments)
        self.set_copyright('Copyright © 2014-2015 Maxime Gauduin')
        self.set_license_type(Gtk.License.GPL_3_0)
        self.set_website('https://github.com/alucryd/pyhenkan')

MainWindow().show_all()
Gtk.main()

# vim: ts=4 sw=4 et:
