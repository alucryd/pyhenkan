import os
import subprocess
import tempfile

from pyhenkan.mediafile import MediaFile
from pyhenkan.plugin import Bilinear, ImageMagickWrite, Trim
from pyhenkan.vapoursynth import VapourSynth

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk


class ScriptCreatorWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='pyanimscript')
        self.set_default_size(640, 480)

        self.wdir = os.environ['HOME']
        self.source = None
        self.vsynth = None

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
        sflt = Gtk.FileFilter()
        sflt.set_name('VapourSynth scripts')
        sflt.add_pattern('*.vpy')

        vext = ['3gp', 'avi', 'flv', 'm2ts', 'mkv', 'mp4', 'ogm', 'webm']
        vflt = Gtk.FileFilter()
        vflt.set_name('Video files')
        for ext in vext:
            vflt.add_pattern('*.' + ext)

        self.open_fcdlg = Gtk.FileChooserDialog('Open Video File', self,
                                                Gtk.FileChooserAction.OPEN,
                                                ('Cancel',
                                                 Gtk.ResponseType.CANCEL,
                                                 'Open', Gtk.ResponseType.OK))
        self.open_fcdlg.set_current_folder(self.wdir)
        self.open_fcdlg.add_filter(vflt)

        self.save_fcdlg = Gtk.FileChooserDialog('Save VapourSynth Script',
                                                self,
                                                Gtk.FileChooserAction.SAVE,
                                                ('Cancel',
                                                 Gtk.ResponseType.CANCEL,
                                                 'Save', Gtk.ResponseType.OK))
        self.save_fcdlg.set_current_folder(self.wdir)
        self.save_fcdlg.add_filter(sflt)

        # --Textview--#
        self.tbuffer = Gtk.TextBuffer()

        tview = Gtk.TextView()
        tview.set_buffer(self.tbuffer)
        tview.set_left_margin(6)
        tview.set_right_margin(6)

        self.add(tview)

    def _update_buffer(self):
        script = self.vsynth.get_script()
        self.tbuffer.set_text(script)

    def on_open_clicked(self, button):
        response = self.open_fcdlg.run()

        if response == Gtk.ResponseType.OK:
            if self.source:
                self.preview_win.destroy()

            f = self.open_fcdlg.get_filename()
            self.source = MediaFile(f)
            self.vsynth = VapourSynth(self.source)

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
        self.vsynth.show_dialog(self)
        if self.source:
            self._update_buffer()


class PreviewWindow(Gtk.Window):
    def __init__(self, source):
        Gtk.Window.__init__(self, title='Preview')

        self.source = source
        self.tempdir = tempfile.gettempdir()
        basename = '/'.join([self.tempdir, 'pyhenkan-preview'])
        self.png = basename + '%d.png'
        self.vpy = basename + '.vpy'

        s = VapourSynth(self.source).get_script()
        with open(self.vpy, 'w') as f:
            f.write(s)

        # Initialize the preview at the middle of the video
        # Pick the first video track for now
        for t in self.source.tracklist:
            if t.type == 'Video':
                tf = t.get_total_frame(self.vpy)
                self.frame = round((tf - 1) / 2)
                break

        self.image = Gtk.Image()

        scrwin = Gtk.ScrolledWindow()
        scrwin.set_min_content_width(848)
        scrwin.set_min_content_height(480)
        scrwin.add(self.image)

        adj = Gtk.Adjustment(self.frame, 0, tf - 1, 1, 10)

        self.spin = Gtk.SpinButton()
        self.spin.set_adjustment(adj)
        self.spin.set_numeric(True)
        self.spin.connect('value-changed', self.on_spin_changed)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,
                                              0, tf - 1, 1)
        self.scale.set_property('hexpand', True)
        self.scale.set_property('halign', Gtk.Align.FILL)
        self.scale.set_draw_value(False)
        self.scale.set_value(self.frame)
        self.scale.connect('value-changed', self.on_scale_changed)

        # Add a mark every 500 frame
        for i in range(0, tf, 500):
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
        filters = self.source.filters
        if not isinstance(filters[len(filters) - 1], ImageMagickWrite):
            bilinear = Bilinear()
            bilinear.format = 'vs.RGB24'
            trim = Trim()
            trim.first = self.frame
            trim.last = self.frame
            imw = ImageMagickWrite()
            imw.imgformat = 'PNG'
            imw.filename = self.png

            filters += [bilinear, trim, imw]

        s = VapourSynth(self.source).get_script()
        with open(self.vpy, 'w') as f:
            f.write(s)

        cmd = 'vspipe "{}" /dev/null'.format(self.vpy)
        subprocess.run(cmd, shell=True,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       universal_newlines=True)

        self.image.set_from_file(self.png.replace('%d', str(0)))

# vim: ts=4 sw=4 et:
