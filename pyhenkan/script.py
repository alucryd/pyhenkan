import os
import tempfile
import vapoursynth as vs

from pyhenkan.mediafile import MediaFile
from pyhenkan.plugin import Bilinear, ImageMagickWrite, ImageMagickHDRIWrite
from pyhenkan.vapoursynth import VapourSynth

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class ScriptCreatorWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='Script Creator')
        self.set_default_size(640, 480)

        self.wdir = os.environ['HOME']
        self.mediafile = MediaFile
        self.vs = VapourSynth

        # --Header Bar-- #
        open_button = Gtk.Button('Open')
        open_button.connect('clicked', self.on_open_clicked)

        self.save_button = Gtk.Button('Save')
        self.save_button.set_sensitive(False)
        self.save_button.connect('clicked', self.on_save_clicked)

        self.preview_button = Gtk.Button('Preview')
        self.preview_button.set_sensitive(False)
        self.preview_button.connect('clicked', self.on_preview_clicked)

        self.filters_button = Gtk.Button('Filters')
        self.filters_button.set_sensitive(False)
        self.filters_button.connect('clicked', self.on_settings_clicked)

        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.pack_start(open_button)
        hbar.pack_start(self.save_button)
        hbar.pack_start(self.preview_button)
        hbar.pack_end(self.filters_button)

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
        script = self.vs.get_script()
        self.tbuffer.set_text(script)

    def on_open_clicked(self, button):
        response = self.open_fcdlg.run()

        if response == Gtk.ResponseType.OK:
            try:
                self.preview_win.destroy()
            except AttributeError:
                pass

            f = self.open_fcdlg.get_filename()
            self.mediafile = MediaFile(f)
            self.vs = VapourSynth(self.mediafile)

            self._update_buffer()
            self.save_button.set_sensitive(True)
            self.preview_button.set_sensitive(True)
            self.filters_button.set_sensitive(True)

        self.open_fcdlg.hide()

    def on_save_clicked(self, button):
        o = '.'.join([self.mediafile.bname, 'vpy'])
        o = '/'.join([self.mediafile.dname, o])

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
        win = PreviewWindow(self.mediafile, self.vs)
        win.show_all()

    def on_settings_clicked(self, button):
        self.vs.show_dialog(self)
        if self.mediafile:
            self._update_buffer()


class PreviewWindow(Gtk.Window):
    def __init__(self, mediafile, vs):
        Gtk.Window.__init__(self, title='Preview')

        self.mediafile = mediafile
        self.vs = vs
        self.tempdir = tempfile.gettempdir()
        basename = '/'.join([self.tempdir, 'pyhenkan-preview'])
        self.png = basename + '%d.png'
        self.vpy = basename + '.vpy'

        # Initialize the preview at the middle of the video
        num_frames = self.vs.get_clip().num_frames
        frame = round((num_frames - 1) / 2)

        self.image = Gtk.Image()

        scrwin = Gtk.ScrolledWindow()
        scrwin.set_min_content_width(848)
        scrwin.set_min_content_height(480)
        scrwin.add(self.image)

        adj = Gtk.Adjustment(frame, 0, num_frames - 1, 1, 10)

        self.spin = Gtk.SpinButton()
        self.spin.set_adjustment(adj)
        self.spin.set_numeric(True)
        self.spin.connect('value-changed', self.on_spin_changed)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,
                                              0, num_frames - 1, 1)
        self.scale.set_property('hexpand', True)
        self.scale.set_property('halign', Gtk.Align.FILL)
        self.scale.set_draw_value(False)
        self.scale.set_value(frame)
        self.scale.connect('value-changed', self.on_scale_changed)

        # Add a mark every 500 frame
        for i in range(0, num_frames, 500):
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

        self.set_frame(frame)

    def on_scale_changed(self, scale):
        value = int(scale.get_value())
        if self.spin.get_value_as_int() != value:
            self.spin.set_value(value)
            self.set_frame(value)

    def on_spin_changed(self, spin):
        value = spin.get_value_as_int()
        if int(self.scale.get_value()) != value:
            self.scale.set_value(value)
            self.set_frame(value)

    def on_refresh_clicked(self, button):
        self.set_frame(self.spin.get_value_as_int())

    def set_frame(self, frame):
        filters = self.mediafile.filters
        bilinear = Bilinear()
        bilinear.args['format'] = vs.RGB24
        imhdriw = ImageMagickHDRIWrite()
        imw = imhdriw if imhdriw.is_avail() else ImageMagickWrite()
        imw.args['imgformat'] = 'PNG'
        imw.args['filename'] = self.png

        # Add the necessary filters
        filters += [bilinear, imw]

        clip = self.vs.get_clip()[frame]
        clip.set_output()
        with open(os.devnull, 'wb') as f:
            clip.output(f)

        # Remove the filters
        filters.pop()
        filters.pop()

        self.image.set_from_file(self.png.replace('%d', str(frame)))

# vim: ts=4 sw=4 et:
