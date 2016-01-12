from collections import OrderedDict

import pyhenkan.plugin as plugin

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk


class VapourSynth:
    def __init__(self, mediafile):
        self.mediafile = mediafile

    def get_script(self):
        script = ['import vapoursynth as vs', 'core = vs.get_core()']
        for f in self.mediafile.filters:
            script.append(f.get_line())
        script.append('clip.set_output()')
        return '\n'.join(script)

    def show_dialog(self, parent):
        dlg = VapourSynthDialog(parent, self.mediafile)
        dlg.run()
        dlg.destroy()


class VapourSynthDialog(Gtk.Dialog):
    def __init__(self, parent, mediafile):
        Gtk.Dialog.__init__(self, 'VapourSynth filters', parent, 0,
                            use_header_bar=1)

        self.mediafile = mediafile
        self.filters = mediafile.filters

        add_button = Gtk.Button()
        add_icon = Gio.ThemedIcon(name='list-add-symbolic')
        add_image = Gtk.Image.new_from_gicon(add_icon, Gtk.IconSize.BUTTON)
        add_button.set_image(add_image)
        add_button.connect('clicked', self.on_add_clicked)

        hbar = self.get_header_bar()
        hbar.pack_start(add_button)

        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(6)
        self.grid.set_row_spacing(6)
        self.grid.set_property('margin', 6)

        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.add(self.grid)

        box = self.get_content_area()
        box.pack_start(self.scrwin, True, True, 0)

        # Plugins
        self.src_plugins = OrderedDict()
        self.src_plugins['ffms2.Source'] = plugin.FFMpegSource
        self.src_plugins['lsmas.LibavSMASHSource'] = plugin.LibavSMASHSource
        self.src_plugins['lsmas.LWLibavSource'] = plugin.LWLibavSource

        self.plugins = OrderedDict()
        self.plugins['std.CropAbs'] = plugin.CropAbs
        self.plugins['std.CropRel'] = plugin.CropRel

        self.plugins['resize.Bilinear'] = plugin.Bilinear
        self.plugins['resize.Bicubic'] = plugin.Bicubic
        self.plugins['resize.Point'] = plugin.Point
        self.plugins['resize.Lanczos'] = plugin.Lanczos
        self.plugins['resize.Spline16'] = plugin.Spline16
        self.plugins['resize.Spline36'] = plugin.Spline36

        self.plugins['flux.SmoothT'] = plugin.FluxSmoothT
        self.plugins['flux.SmoothST'] = plugin.FluxSmoothST
        self.plugins['rgvs.RemoveGrain'] = plugin.RemoveGrain
        self.plugins['focus.TemporalSoften'] = plugin.TemporalSoften

        self.plugins['f3kdb.Deband'] = plugin.F3kdb

        self.plugins['std.Trim'] = plugin.Trim

        self._populate_grid()

    def _populate_grid(self):
        for child in self.grid.get_children():
            self.grid.remove(child)

        trim = False
        for f in self.filters:
            if f is not None and f.function == 'Trim':
                trim = True
                break

        for i in range(len(self.filters)):
            f = self.filters[i]
            if f is not None:
                active = '.'.join([f.namespace, f.function])
            else:
                active = ''

            conf_icon = Gio.ThemedIcon(name='applications-system-symbolic')
            conf_image = Gtk.Image.new_from_gicon(conf_icon,
                                                  Gtk.IconSize.BUTTON)
            conf_button = Gtk.Button()
            conf_button.set_image(conf_image)
            conf_button.set_sensitive(False)
            conf_button.connect('clicked', self.on_conf_clicked, i)

            up_button = Gtk.Button()
            up_icon = Gio.ThemedIcon(name='go-up-symbolic')
            up_image = Gtk.Image.new_from_gicon(up_icon, Gtk.IconSize.BUTTON)
            up_button.set_image(up_image)
            up_button.connect('clicked', self.on_move_clicked, 'up', i)

            down_button = Gtk.Button()
            down_icon = Gio.ThemedIcon(name='go-down-symbolic')
            down_image = Gtk.Image.new_from_gicon(down_icon,
                                                  Gtk.IconSize.BUTTON)
            down_button.set_image(down_image)
            down_button.connect('clicked', self.on_move_clicked, 'down', i)

            remove_button = Gtk.Button()
            remove_icon = Gio.ThemedIcon(name='list-remove-symbolic')
            remove_image = Gtk.Image.new_from_gicon(remove_icon,
                                                    Gtk.IconSize.BUTTON)
            remove_button.set_image(remove_image)
            remove_button.connect('clicked', self.on_remove_clicked, i)

            plugin_cbtext = Gtk.ComboBoxText()
            plugin_cbtext.set_property('hexpand', True)
            plugins = self.src_plugins if i == 0 else self.plugins
            j = 0
            for p in plugins:
                # Can't trim several times
                # Make 2 tests because flake8 is not happy with multiline tests
                if p != 'std.Trim':
                    plugin_cbtext.append_text(p)
                else:
                    if active == 'std.Trim' or not trim:
                        plugin_cbtext.append_text(p)
                if p == active:
                    plugin_cbtext.set_active(j)
                    conf_button.set_sensitive(True)
                    if p == 'std.Trim':
                        trim = True
                j += 1
            plugin_cbtext.connect('changed', self.on_plugin_changed, i)

            if i == 0:
                up_button.set_sensitive(False)
                down_button.set_sensitive(False)
                remove_button.set_sensitive(False)
            elif i == 1:
                up_button.set_sensitive(False)

            if i == len(self.filters) - 1:
                down_button.set_sensitive(False)

            self.grid.attach(plugin_cbtext, 0, i, 1, 1)
            self.grid.attach_next_to(conf_button, plugin_cbtext,
                                     Gtk.PositionType.RIGHT, 1, 1)
            self.grid.attach_next_to(up_button, conf_button,
                                     Gtk.PositionType.RIGHT, 1, 1)
            self.grid.attach_next_to(down_button, up_button,
                                     Gtk.PositionType.RIGHT, 1, 1)
            self.grid.attach_next_to(remove_button, down_button,
                                     Gtk.PositionType.RIGHT, 1, 1)

        if len(self.filters) <= 6:
            self.scrwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
            self.resize(1, 1)
        else:
            self.scrwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)

        self.show_all()

    def on_add_clicked(self, button):
        self.filters.append(None)

        self._populate_grid()

    def on_remove_clicked(self, button, i):
        if self.filters[i].function == 'Trim':
            self.mediafile.first = 0
            self.mediafile.last = 0
        self.filters.pop(i)

        self._populate_grid()

    def on_move_clicked(self, button, direction, i):
        if direction == 'up':
            self.filters[i - 1:i + 1] = [self.filters[i],
                                         self.filters[i - 1]]
        elif direction == 'down':
            self.filters[i:i + 2] = [self.filters[i + 1],
                                     self.filters[i]]
        self._populate_grid()

    def on_plugin_changed(self, combo, i):
        p = combo.get_active_text()
        if i == 0:
            self.filters[i] = self.src_plugins[p](self.mediafile.path)
            self.filters[i].args['fpsnum'] = self.mediafile.fpsnum
            self.filters[i].args['fpsden'] = self.mediafile.fpsden
        else:
            self.filters[i] = self.plugins[p]()
        if p.startswith('resize'):
            self.filters[i].args['width'] = self.mediafile.width
            self.filters[i].args['height'] = self.mediafile.height
        elif p == 'std.Trim':
            self.filters[i].args['first'] = self.mediafile.first
            self.filters[i].args['last'] = self.mediafile.last

        self._populate_grid()

    def on_conf_clicked(self, button, i):
        self.filters[i].show_dialog(self)
        if i == 0:
            self.mediafile.fpsnum = self.filters[i].args['fpsnum']
            self.mediafile.fpsden = self.filters[i].args['fpsden']
        elif self.filters[i].namespace == 'resize':
            self.mediafile.width = self.filters[i].args['width']
            self.mediafile.height = self.filters[i].args['height']
        elif self.filters[i].function == 'Trim':
            self.mediafile.first = self.filters[i].args['first']
            self.mediafile.last = self.filters[i].args['last']

# vim: ts=4 sw=4 et:
