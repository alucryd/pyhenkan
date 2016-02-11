from collections import OrderedDict

import vapoursynth as vs

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class Plugin:
    def __init__(self, namespace, function, dialog):
        self.namespace = namespace
        self.function = function
        self.args = OrderedDict()
        self.dialog = dialog

    def is_avail(self):
        plugins = vs.get_core().get_plugins()
        plugins = [[plugins[p]['namespace'],
                   [f for f in plugins[p]['functions']]] for p in plugins]
        plugins = {p[0]: p[1] for p in plugins}
        return self.function in plugins.get(self.namespace, [])

    def show_dialog(self, parent):
        dlg = self.dialog(self, parent)
        dlg.run()
        dlg.destroy()

    def get_line(self, args=['clip']):
        if args:
            args = ['clip']
        for key in self.args:
            value = self.args[key]
            if type(value) is str:
                arg = key + '="{}"'
            else:
                arg = key + '={}'
            arg = arg.format(value)
            args.append(arg)
        line = 'clip = core.{}.{}({})'.format(self.namespace, self.function,
                                              ', '.join(args))
        return line


class SourcePlugin(Plugin):
    def __init__(self, namespace, function, dialog, source):
        Plugin.__init__(self, namespace, function, dialog)

        self.args['source'] = source
        self.args['fpsnum'] = 0
        self.args['fpsden'] = 1
        # self.args['threads'] = 0

    def get_line(self):
        return super().get_line([])


class LibavSMASHSource(SourcePlugin):
    def __init__(self, source):
        SourcePlugin.__init__(self, 'lsmas', 'LibavSMASHSource',
                              LibavSMASHSourceDialog, source)

        self.args['track'] = 0
        # self.args['seek_mode'] = 0
        # self.args['seek_threshold'] = 10
        # self.args['dr'] = 0
        # self.args['variable'] = 0
        # self.args['format'] = ''
        # self.args['decoder'] = ''


class LWLibavSource(SourcePlugin):
    def __init__(self, source):
        SourcePlugin.__init__(self, 'lsmas', 'LWLibavSource',
                              LWLibavSourceDialog, source)

        self.args['stream_index'] = -1
        # self.args['cache'] = 1
        # self.args['seek_mode'] = 0
        # self.args['seek_threshold'] = 10
        # self.args['dr'] = 0
        # self.args['variable'] = 0
        # self.args['format'] = ''
        # self.args['repeat'] = 0
        # self.args['dominance'] = 1
        # self.args['decoder'] = ''


class FFmpegSource(SourcePlugin):
    def __init__(self, source):
        SourcePlugin.__init__(self, 'ffms2', 'Source',
                              FFMpegSourceDialog, source)

        self.args['track'] = -1
        # self.args['cache'] = True
        # self.args['cachefile'] = self.source + '.ffindex'
        # self.args['timecodes'] = ''
        # self.args['seekmode'] = 1
        # self.args['width'] = -1
        # self.args['height'] = -1
        # self.args['resizer'] = 'BICUBIC'
        # self.args['format'] = -1
        # self.args['alpha'] = True


class ImageMagickWrite(Plugin):
    def __init__(self):
        Plugin.__init__(self, 'imwri', 'Write', None)

        self.args['imgformat'] = ''
        self.args['filename'] = ''


class CropPlugin(Plugin):
    def __init__(self, namespace, function, dialog):
        Plugin.__init__(self, namespace, function, dialog)


class CropAbs(CropPlugin):
    def __init__(self):
        CropPlugin.__init__(self, 'std', 'CropAbs', CropAbsDialog)

        self.args['width'] = 0
        self.args['height'] = 0
        self.args['left'] = 0
        self.args['top'] = 0


class CropRel(CropPlugin):
    def __init__(self):
        CropPlugin.__init__(self, 'std', 'CropRel', CropRelDialog)

        self.args['left'] = 0
        self.args['right'] = 0
        self.args['top'] = 0
        self.args['bottom'] = 0


class ResizePlugin(Plugin):
    def __init__(self, function):
        Plugin.__init__(self, 'resize', function, ResizePluginDialog)

        self.args['width'] = 0
        self.args['height'] = 0
        self.args['format'] = 0
        # self.args['matrix'] = ''
        # self.args['transfer'] = ''
        # self.args['primaries'] = ''
        # self.args['range'] = ''
        # self.args['chromaloc'] = ''
        # self.args['matrix_in'] = ''
        # self.args['transfer_in'] = ''
        # self.args['primaries_in'] = ''
        # self.args['range_in'] = ''
        # self.args['chromaloc_in'] = ''
        # self.args['plugin_param_a'] = 0.0
        # self.args['plugin_param_b'] = 0.0
        # self.args['resample_plugin_uv'] = ''
        # self.args['resample_plugin_uv_a'] = 0.0
        # self.args['resample_plugin_uv_b'] = 0.0
        # self.args['dither_type'] = ''


class Bilinear(ResizePlugin):
    def __init__(self):
        ResizePlugin.__init__(self, 'Bilinear')


class Bicubic(ResizePlugin):
    def __init__(self):
        ResizePlugin.__init__(self, 'Bicubic')


class Point(ResizePlugin):
    def __init__(self):
        ResizePlugin.__init__(self, 'Point')


class Lanczos(ResizePlugin):
    def __init__(self):
        ResizePlugin.__init__(self, 'Lanczos')


class Spline16(ResizePlugin):
    def __init__(self):
        ResizePlugin.__init__(self, 'Spline16')


class Spline36(ResizePlugin):
    def __init__(self):
        ResizePlugin.__init__(self, 'Spline36')


class DenoisePlugin(Plugin):
    def __init__(self, namespace, function, dialog):
        Plugin.__init__(self, namespace, function, dialog)


class FluxSmoothT(DenoisePlugin):
    def __init__(self):
        DenoisePlugin.__init__(self, 'flux', 'SmoothT', FluxSmoothTDialog)

        self.args['temporal_threshold'] = 7
        self.args['planes'] = [0, 1, 2]


class FluxSmoothST(DenoisePlugin):
    def __init__(self):
        DenoisePlugin.__init__(self, 'flux', 'SmoothT', FluxSmoothSTDialog)

        self.args['spatial_threshold'] = 7
        self.args['temporal_threshold'] = 7
        self.args['planes'] = [0, 1, 2]


class RemoveGrain(DenoisePlugin):
    def __init__(self):
        DenoisePlugin.__init__(self, 'rgvs', 'RemoveGrain', RemoveGrainDialog)

        self.args['mode'] = [2, 2, 2]


class TemporalSoften(DenoisePlugin):
    def __init__(self):
        DenoisePlugin.__init__(self, 'focus', 'TemporalSoften',
                               TemporalSoftenDialog)

        self.args['radius'] = 4
        self.args['luma_threshold'] = 4
        self.args['chroma_threshold'] = 4
        self.args['scenechange'] = 0
        # self.mode = 2


class DebandPlugin(Plugin):
    def __init__(self, namespace, function, dialog):
        Plugin.__init__(self, namespace, function, dialog)


class F3kdb(DebandPlugin):
    def __init__(self):
        DebandPlugin.__init__(self, 'f3kdb', 'Deband', F3kdbDialog)

        # self.args['range'] = 15
        self.args['y'] = 64
        self.args['cb'] = 64
        self.args['cr'] = 64
        self.args['grainy'] = 64
        self.args['grainc'] = 64
        self.args['sample_mode'] = 2
        # self.args['seed'] = None
        self.args['blur_first'] = True
        self.args['dynamic_grain'] = False
        # self.args['opt'] = -1
        self.args['dither_algo'] = 3
        # self.args['keep_tv_range'] = False
        self.args['output_depth'] = 8
        # self.args['random_algo_ref'] = 1
        # self.args['random_algo_grain'] = 1
        # self.args['random_param_ref'] = 1.0
        # self.args['random_param_grain'] = 1.0


class MiscPlugin(Plugin):
    def __init__(self, namespace, function, dialog):
        Plugin.__init__(self, namespace, function, dialog)


class Trim(MiscPlugin):
    def __init__(self):
        MiscPlugin.__init__(self, 'std', 'Trim', TrimDialog)

        self.args['first'] = 0
        self.args['last'] = 0


class PluginDialog(Gtk.Dialog):
    def __init__(self, plugin, parent):
        title = '.'.join([plugin.namespace, plugin.function])
        Gtk.Dialog.__init__(self, title, parent, Gtk.DialogFlags.MODAL)
        self.set_default_size(240, 0)

        self.plugin = plugin

        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(6)
        self.grid.set_row_spacing(6)
        self.grid.set_property('margin', 6)

        vbox = self.get_content_area()
        vbox.add(self.grid)

    def populate_grid(self, widgets):
        for i in range(len(widgets)):
            wl = widgets[i]
            if type(wl[1]) is list:
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                for w in wl[1]:
                    hbox.pack_start(w, True, True, 0)
                wl[1] = hbox
            self.grid.attach(wl[0], 0, i, 1, 1)
            self.grid.attach_next_to(wl[1], wl[0],
                                     Gtk.PositionType.RIGHT, 1, 1)
        self.show_all()

    def label(self, name):
        label = Gtk.Label(name)
        label.set_halign(Gtk.Align.CENTER)
        return label

    def spin(self, key, adj):
        spin = Gtk.SpinButton()
        spin.set_adjustment(adj)
        spin.set_numeric(True)
        spin.set_property('hexpand', True)
        spin.set_value(self.plugin.args[key])
        spin.connect('value_changed', self.on_spin_changed, key)
        return spin

    def on_spin_changed(self, spin, key):
        self.plugin.args[key] = spin.get_value_as_int()

    def cbtext(self, key, text):
        cbtext = Gtk.ComboBoxText()
        cbtext.set_property('hexpand', True)
        for t in text:
            cbtext.append_text(t)
            if text.index(t) == self.plugin.args[key] - 1:
                cbtext.set_active(text.index(t))
        cbtext.connect('changed', self.on_cbtext_changed, key, text)
        return cbtext

    def on_cbtext_changed(self, cbtext, key, text):
        self.plugin.args[key] = text.index(cbtext.get_active_text()) + 1

    def check(self, key):
        check = Gtk.CheckButton()
        check.set_active(self.plugin.args[key])
        check.connect('toggled', self.on_check_toggled, key)
        return check

    def on_check_toggled(self, check, key):
        self.plugin.args[key] = check.get_active()


class SourcePluginDialog(PluginDialog):
    def __init__(self, plugin, parent):
        PluginDialog.__init__(self, plugin, parent)

        fpsnums = Gtk.Adjustment(0, 0, 300000, 1, 100)
        fpsdens = Gtk.Adjustment(1, 1, 300000, 1, 100)

        widgets = [[self.label('FPS Numerator'),
                    self.spin('fpsnum', fpsnums)],
                   [self.label('FPS Denominator'),
                    self.spin('fpsden', fpsdens)]]

        self.populate_grid(widgets)


class LibavSMASHSourceDialog(SourcePluginDialog):
    def __init__(self, plugin, parent):
        SourcePluginDialog.__init__(self, plugin, parent)


class LWLibavSourceDialog(SourcePluginDialog):
    def __init__(self, plugin, parent):
        SourcePluginDialog.__init__(self, plugin, parent)


class FFMpegSourceDialog(SourcePluginDialog):
    def __init__(self, plugin, parent):
        SourcePluginDialog.__init__(self, plugin, parent)


class CropAbsDialog(PluginDialog):
    def __init__(self, plugin, parent):
        PluginDialog.__init__(self, plugin, parent)

        widths = Gtk.Adjustment(0, 0, 3840, 1, 10)
        heights = Gtk.Adjustment(0, 0, 2160, 1, 10)
        lefts = Gtk.Adjustment(0, 0, 3840, 1, 10)
        tops = Gtk.Adjustment(0, 0, 2160, 1, 10)

        widgets = [[self.label('Width'), self.spin('width', widths)],
                   [self.label('Height'), self.spin('height', heights)],
                   [self.label('Left'), self.spin('left', lefts)],
                   [self.label('Top'), self.spin('top', tops)]]

        self.populate_grid(widgets)


class CropRelDialog(PluginDialog):
    def __init__(self, plugin, parent):
        PluginDialog.__init__(self, plugin, parent)

        lefts = Gtk.Adjustment(0, 0, 3840, 1, 10)
        rights = Gtk.Adjustment(0, 0, 3840, 1, 10)
        tops = Gtk.Adjustment(0, 0, 2160, 1, 10)
        bottoms = Gtk.Adjustment(0, 0, 2160, 1, 10)

        widgets = [[self.label('Left'), self.spin('left', lefts)],
                   [self.label('Right'), self.spin('right', rights)],
                   [self.label('Top'), self.spin('top', tops)],
                   [self.label('Bottom'), self.spin('bottom', bottoms)]]

        self.populate_grid(widgets)


class ResizePluginDialog(PluginDialog):
    def __init__(self, plugin, parent):
        PluginDialog.__init__(self, plugin, parent)

        widths = Gtk.Adjustment(0, 0, 3840, 1, 10)
        heights = Gtk.Adjustment(0, 0, 2160, 1, 10)
        formats = ['GRAY8', 'GRAY16', 'GRAYH', 'GRAYS', 'YUV420P8', 'YUV422P8',
                   'YUV444P8', 'YUV410P8', 'YUV411P8', 'YUV440P8', 'YUV420P9',
                   'YUV422P9', 'YUV444P9', 'YUV420P10', 'YUV422P10',
                   'YUV444P10', 'YUV420P16', 'YUV422P16', 'YUV444P16',
                   'YUV444PH', 'YUV444PS', 'RGB24', 'RGB27', 'RGB30', 'RGB48',
                   'RGBH', 'RGBS', 'COMPATBGR32', 'COMPATYUY2']

        widgets = [[self.label('Width'), self.spin('width', widths)],
                   [self.label('Height'), self.spin('height', heights)],
                   [self.label('Format'), self.cbtext('format', formats)]]

        self.populate_grid(widgets)


class FluxSmoothTDialog(PluginDialog):
    def __init__(self, plugin, parent):
        PluginDialog.__init__(self, plugin, parent)

        t_thresholds = Gtk.Adjustment(7, -1, 255, 1, 10)

        widgets = [[self.label('Temporal Threshold'),
                    self.spin('temporal_threshold', t_thresholds)],
                   [self.label('Planes'),
                    [self.check('planes', 'Y', 0),
                     self.check('planes', 'U', 1),
                     self.check('planes', 'V', 2)]]]

        self.populate_grid(widgets)

    def check(self, key, name, value):
        check = Gtk.CheckButton()
        check.set_label(name)
        check.set_active(value in self.plugin.args[key])
        check.connect('toggled', self.on_check_toggled, key, value)
        return check

    def on_check_toggled(self, check, key, value):
        if check.get_active():
            self.plugin.args[key].append(value)
            self.plugin.args[key].sort()
        else:
            self.plugin.args[key].remove(value)


class FluxSmoothSTDialog(PluginDialog):
    def __init__(self, plugin, parent):
        PluginDialog.__init__(self, plugin, parent)

        s_thresholds = Gtk.Adjustment(7, -1, 255, 1, 10)
        t_thresholds = Gtk.Adjustment(7, -1, 255, 1, 10)

        widgets = [[self.label('Spatial Threshold'),
                    self.spin('spatial_threshold', s_thresholds)],
                   [self.label('Temporal Threshold'),
                    self.spin('temporal_threshold', t_thresholds)],
                   [self.label('Planes'),
                    [self.check('planes', 'Y', 0),
                     self.check('planes', 'U', 1),
                     self.check('planes', 'V', 2)]]]

        self.populate_grid(widgets)

    def check(self, key, name, value):
        check = Gtk.CheckButton()
        check.set_label(name)
        check.set_active(value in self.plugin.args[key])
        check.connect('toggled', self.on_check_toggled, key, value)
        return check

    def on_check_toggled(self, check, key, value):
        if check.get_active():
            self.plugin.args[key].append(value)
            self.plugin.args[key].sort()
        else:
            self.plugin.args[key].remove(value)


class RemoveGrainDialog(PluginDialog):
    def __init__(self, plugin, parent):
        PluginDialog.__init__(self, plugin, parent)

        modes_y = Gtk.Adjustment(2, 0, 18, 1, 10)
        modes_u = Gtk.Adjustment(2, 0, 18, 1, 10)
        modes_v = Gtk.Adjustment(2, 0, 18, 1, 10)

        widgets = [[self.label('Y Mode'), self.spin('mode', modes_y, 0)],
                   [self.label('U Mode'), self.spin('mode', modes_u, 1)],
                   [self.label('V Mode'), self.spin('mode', modes_v, 2)]]

        self.populate_grid(widgets)

    def spin(self, key, adj, idx):
        spin = Gtk.SpinButton()
        spin.set_adjustment(adj)
        spin.set_numeric(True)
        spin.set_property('hexpand', True)
        spin.set_value(self.plugin.args[key][idx])
        spin.connect('value_changed', self.on_spin_changed, key, idx)
        return spin

    def on_spin_changed(self, spin, key, idx):
        self.plugin.args[key][idx] = spin.get_value_as_int()


class TemporalSoftenDialog(PluginDialog):
    def __init__(self, plugin, parent):
        PluginDialog.__init__(self, plugin, parent)

        radii = Gtk.Adjustment(4, 1, 7, 1, 1)
        l_thresholds = Gtk.Adjustment(4, 0, 255, 1, 10)
        c_thresholds = Gtk.Adjustment(4, 0, 255, 1, 10)
        scenechanges = Gtk.Adjustment(0, 0, 254, 1, 10)

        widgets = [[self.label('Radius'), self.spin('radius', radii)],
                   [self.label('Luma Threshold'),
                    self.spin('luma_threshold', l_thresholds)],
                   [self.label('Chroma Threshold'),
                    self.spin('chroma_threshold', c_thresholds)],
                   [self.label('Scene Change'),
                    self.spin('scenechange', scenechanges)]]

        self.populate_grid(widgets)


class F3kdbDialog(PluginDialog):
    def __init__(self, plugin, parent):
        PluginDialog.__init__(self, plugin, parent)

        ys = Gtk.Adjustment(64, 0, 80, 1, 10)
        cbs = Gtk.Adjustment(64, 0, 80, 1, 10)
        crs = Gtk.Adjustment(64, 0, 80, 1, 10)
        grainys = Gtk.Adjustment(64, 0, 80, 1, 10)
        graincs = Gtk.Adjustment(64, 0, 80, 1, 10)
        sample_modes = ['2 pixels', '4 pixels']
        dither_algos = ['None', 'Ordered', 'Floyd-Steinberg']
        output_depths = Gtk.Adjustment(8, 8, 16, 1, 1)

        widgets = [[self.label('Y'), self.spin('y', ys)],
                   [self.label('Cb'), self.spin('cb', cbs)],
                   [self.label('Cr'), self.spin('cr', crs)],
                   [self.label('Y Grain'), self.spin('grainy', grainys)],
                   [self.label('C Grain'), self.spin('grainc', graincs)],
                   [self.label('Sample Mode'),
                    self.cbtext('sample_mode', sample_modes)],
                   [self.label('Blur First'), self.check('blur_first')],
                   [self.label('Dynamic Grain'), self.check('dynamic_grain')],
                   [self.label('Dithering'),
                    self.cbtext('dither_algo', dither_algos)],
                   [self.label('Output Depth'),
                    self.spin('output_depth', output_depths)]]

        self.populate_grid(widgets)


class TrimDialog(PluginDialog):
    def __init__(self, plugin, parent):
        PluginDialog.__init__(self, plugin, parent)

        firsts = Gtk.Adjustment(0, 0, 1000000, 1, 100)
        lasts = Gtk.Adjustment(0, 0, 1000000, 1, 100)

        widgets = [[self.label('First'), self.spin('first', firsts)],
                   [self.label('Last'), self.spin('last', lasts)]]

        self.populate_grid(widgets)

# vim: ts=4 sw=4 et:
