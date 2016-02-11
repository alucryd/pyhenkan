from collections import OrderedDict

import pyhenkan.codec as codec
import pyhenkan.plugin as plugin

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class Environment:
    def __init__(self):
        # Codecs
        self.vencs = OrderedDict()
        self.vencs['VP8 (libvpx)'] = [codec.Vp8, False]
        self.vencs['VP9 (libvpx)'] = [codec.Vp9, False]
        self.vencs['AVC (libx264)'] = [codec.X264, False]
        self.vencs['HEVC (libx265)'] = [codec.X265, False]

        self.aencs = OrderedDict()
        self.aencs['AAC (native)'] = [codec.Aac, False]
        self.aencs['AAC (libfaac)'] = [codec.Faac, False]
        self.aencs['AAC (libfdk-aac)'] = [codec.Fdkaac, False]
        self.aencs['FLAC (native)'] = [codec.Flac, False]
        self.aencs['MP3 (libmp3lame)'] = [codec.Lame, False]
        self.aencs['Opus (libopus)'] = [codec.Opus, False]
        self.aencs['Vorbis (libvorbis)'] = [codec.Vorbis, False]

        self.adecs = OrderedDict()
        self.adecs['DTS (libdcadec)'] = [codec.Dcadec, False]

        self.arsps = OrderedDict()
        self.arsps['Software (native)'] = [codec.Swr, False]
        self.arsps['SoX (libsoxr)'] = [codec.Soxr, False]

        # Plugins
        self.source_plugins = OrderedDict()
        self.source_plugins['FFmpegSource'] = [plugin.FFmpegSource, False]
        self.source_plugins['LibavSMASHSource'] = [plugin.LibavSMASHSource,
                                                   False]
        self.source_plugins['LWLibavSource'] = [plugin.LWLibavSource, False]

        self.crop_plugins = OrderedDict()
        self.crop_plugins['Absolute Crop'] = [plugin.CropAbs, False]
        self.crop_plugins['Relative Crop'] = [plugin.CropRel, False]

        self.resize_plugins = OrderedDict()
        self.resize_plugins['Bilinear'] = [plugin.Bilinear, False]
        self.resize_plugins['Bicubic'] = [plugin.Bicubic, False]
        self.resize_plugins['Point'] = [plugin.Point, False]
        self.resize_plugins['Lanczos'] = [plugin.Lanczos, False]
        self.resize_plugins['Spline16'] = [plugin.Spline16, False]
        self.resize_plugins['Spline36'] = [plugin.Spline36, False]

        self.denoise_plugins = OrderedDict()
        self.denoise_plugins['FluxSmoothT'] = [plugin.FluxSmoothT, False]
        self.denoise_plugins['FluxSmoothST'] = [plugin.FluxSmoothST, False]
        self.denoise_plugins['RemoveGrain'] = [plugin.RemoveGrain, False]
        self.denoise_plugins['TemporalSoften'] = [plugin.TemporalSoften, False]

        self.deband_plugins = OrderedDict()
        self.deband_plugins['f3kdb'] = [plugin.F3kdb, False]

        self.misc_plugins = OrderedDict()
        self.misc_plugins['Trim'] = [plugin.Trim, False]

        self.check_codecs()
        self.check_plugins()

    def check_codecs(self):
        for attr in ['vencs', 'aencs', 'adecs', 'arsps']:
            codecs = getattr(self, attr)
            for c in codecs:
                codecs[c][1] = codecs[c][0]().is_avail()

    def check_plugins(self):
        for attr in [d + '_plugins' for d in ['source', 'crop', 'resize',
                                              'denoise', 'deband', 'misc']]:
            plugins = getattr(self, attr)
            for p in plugins:
                if attr == 'source_plugins':
                    plugins[p][1] = plugins[p][0]('').is_avail()
                else:
                    plugins[p][1] = plugins[p][0]().is_avail()

    def show_window(self, parent):
        win = EnvironmentWindow(self, parent)
        win.show_all()


class EnvironmentWindow(Gtk.Window):
    def __init__(self, env, parent):
        Gtk.Window.__init__(self, title='Environment')
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(480, 480)

        self.env = env

        lstore = Gtk.ListStore(str)
        treeiter = lstore.append(['FFmpeg codecs'])
        lstore.append(['VapourSynth plugins'])

        crtext = Gtk.CellRendererText()
        tvcolumn = Gtk.TreeViewColumn('', crtext, text=0)
        tview = Gtk.TreeView(lstore)
        tview.set_headers_visible(False)
        tview.append_column(tvcolumn)

        selection = tview.get_selection()
        selection.select_iter(treeiter)
        selection.connect('changed', self.on_select_changed)

        # Header bar
        refresh_button = Gtk.Button('Refresh')
        refresh_button.connect('clicked', self.on_refresh_clicked, selection)

        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.set_title('Environment')
        hbar.pack_start(refresh_button)

        self.set_titlebar(hbar)

        self.codecs()
        self.plugins()

        self.vport = Gtk.Viewport()
        self.vport.set_hscroll_policy(Gtk.ScrollablePolicy.MINIMUM)
        self.vport.set_vscroll_policy(Gtk.ScrollablePolicy.NATURAL)
        self.vport.add(self.codecs())

        scrwin = Gtk.ScrolledWindow()
        scrwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrwin.add(self.vport)

        hbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(tview, False, True, 0)
        hbox.pack_start(scrwin, True, True, 0)

        self.add(hbox)

    def codecs(self):
        grid = Gtk.Grid()
        grid.set_property('margin', 6)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        grid.set_row_homogeneous(True)

        vencs_label = Gtk.Label()
        vencs_label.set_markup('<b>Video encoders</b>')
        vencs_label.set_halign(Gtk.Align.START)
        aencs_label = Gtk.Label()
        aencs_label.set_markup('<b>Audio encoders</b>')
        aencs_label.set_halign(Gtk.Align.START)
        adecs_label = Gtk.Label()
        adecs_label.set_markup('<b>Audio decoders</b>')
        adecs_label.set_halign(Gtk.Align.START)
        arsps_label = Gtk.Label()
        arsps_label.set_markup('<b>Audio resamplers</b>')
        arsps_label.set_halign(Gtk.Align.START)

        i = 0
        for attr in ['vencs', 'aencs', 'adecs', 'arsps']:
            label = eval(attr + '_label')
            codecs = getattr(self.env, attr)

            grid.attach(label, 0, i, 2, 1)
            i += 1

            for c in codecs:
                label = Gtk.Label(c)
                label.set_halign(Gtk.Align.START)
                grid.attach(label, 0, i, 1, 1)

                label = Gtk.Label()
                label.set_halign(Gtk.Align.START)
                if codecs[c][1]:
                    label.set_text('Found')
                else:
                    label.set_text('Not Found')
                grid.attach(label, 1, i, 1, 1)
                i += 1

        return grid

    def plugins(self):
        grid = Gtk.Grid()
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        grid.set_row_homogeneous(True)

        source_label = Gtk.Label()
        source_label.set_markup('<b>Source plugins</b>')
        source_label.set_halign(Gtk.Align.START)
        crop_label = Gtk.Label()
        crop_label.set_markup('<b>Crop plugins</b>')
        crop_label.set_halign(Gtk.Align.START)
        resize_label = Gtk.Label()
        resize_label.set_markup('<b>Resize plugins</b>')
        resize_label.set_halign(Gtk.Align.START)
        denoise_label = Gtk.Label()
        denoise_label.set_markup('<b>Denoise plugins</b>')
        denoise_label.set_halign(Gtk.Align.START)
        deband_label = Gtk.Label()
        deband_label.set_markup('<b>Deband plugins</b>')
        deband_label.set_halign(Gtk.Align.START)
        misc_label = Gtk.Label()
        misc_label.set_markup('<b>Misc plugins</b>')
        misc_label.set_halign(Gtk.Align.START)

        i = 0
        for attr in ['source', 'crop', 'resize', 'denoise', 'deband', 'misc']:
            label = eval(attr + '_label')
            plugins = getattr(self.env, attr + '_plugins')

            grid.attach(label, 0, i, 2, 1)
            i += 1

            for p in plugins:
                label = Gtk.Label(p)
                label.set_halign(Gtk.Align.START)
                grid.attach(label, 0, i, 1, 1)

                label = Gtk.Label()
                label.set_halign(Gtk.Align.START)
                if plugins[p][1]:
                    label.set_text('Found')
                else:
                    label.set_text('Not Found')
                grid.attach(label, 1, i, 1, 1)
                i += 1

        return grid

    def on_select_changed(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            self.vport.remove(self.vport.get_children()[0])
            print(model[treeiter][0])
            if model[treeiter][0] == 'FFmpeg codecs':
                self.vport.add(self.codecs())
            elif model[treeiter][0] == 'VapourSynth plugins':
                self.vport.add(self.plugins())
            self.show_all()

    def on_refresh_clicked(self, button, selection):
        self.env.check_codecs()
        self.env.check_plugins()
        self.on_select_changed(selection)

# vim: ts=4 sw=4 et:
