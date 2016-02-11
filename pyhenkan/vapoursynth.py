import pyhenkan.plugin as plugin
from pyhenkan.environment import Environment

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

        # Get environment
        self.env = Environment()

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

        self._populate_grid()

    def _populate_grid(self):
        for child in self.grid.get_children():
            self.grid.remove(child)

        for i in range(len(self.filters)):
            f = self.filters[i]

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

            type_cbtext = Gtk.ComboBoxText()
            type_cbtext.set_property('hexpand', True)
            if i == 0:
                plugins = self.env.source_plugins
                type_cbtext.append_text('Source')
                type_cbtext.set_active(0)
                type_cbtext.set_sensitive(False)
            else:
                type_cbtext.append_text('Crop')
                type_cbtext.append_text('Resize')
                type_cbtext.append_text('Denoise')
                type_cbtext.append_text('Deband')
                type_cbtext.append_text('Misc')

            if i > 0 and f is not None:
                if isinstance(f, plugin.CropPlugin):
                    plugins = self.env.crop_plugins
                    type_cbtext.set_active(0)
                elif isinstance(f, plugin.ResizePlugin):
                    plugins = self.env.resize_plugins
                    type_cbtext.set_active(1)
                elif isinstance(f, plugin.DenoisePlugin):
                    plugins = self.env.denoise_plugins
                    type_cbtext.set_active(2)
                elif isinstance(f, plugin.DebandPlugin):
                    plugins = self.env.deband_plugins
                    type_cbtext.set_active(3)
                elif isinstance(f, plugin.MiscPlugin):
                    plugins = self.env.misc_plugins
                    type_cbtext.set_active(4)

            type_cbtext.connect('changed', self.on_type_changed, i)

            plugin_cbtext = Gtk.ComboBoxText()
            plugin_cbtext.set_property('hexpand', True)

            j = 0
            if f is not None:
                for p in plugins:
                    if plugins[p][1]:
                        plugin_cbtext.append_text(p)
                        if isinstance(f, plugins[p][0]):
                            plugin_cbtext.set_active(j)
                            conf_button.set_sensitive(True)
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

            self.grid.attach(type_cbtext, 0, i, 1, 1)
            self.grid.attach_next_to(plugin_cbtext, type_cbtext,
                                     Gtk.PositionType.RIGHT, 1, 1)
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

    def on_type_changed(self, cbtext, i):
        plugin_cbtext = Gtk.ComboBoxText()
        plugin_cbtext.set_property('hexpand', True)
        plugin_cbtext.connect('changed', self.on_plugin_changed, i)
        self.grid.remove(self.grid.get_child_at(1, i))
        self.grid.attach(plugin_cbtext, 1, i, 1, 1)
        self.filters[i] = None

        t = cbtext.get_active_text()
        if t == 'Crop':
            plugins = self.env.crop_plugins
        elif t == 'Resize':
            plugins = self.env.resize_plugins
        elif t == 'Denoise':
            plugins = self.env.denoise_plugins
        elif t == 'Deband':
            plugins = self.env.deband_plugins
        elif t == 'Misc':
            plugins = self.env.misc_plugins

        # Trimming several times is a bad idea
        trim = False
        for f in self.filters:
            if isinstance(f, plugin.Trim):
                trim = True

        for p in plugins:
            if not (p == 'Trim' and trim):
                plugin_cbtext.append_text(p)

        self.show_all()

    def on_plugin_changed(self, cbtext, i):
        p = cbtext.get_active_text()
        type_cbtext = self.grid.get_child_at(0, i)
        t = type_cbtext.get_active_text()
        path = self.mediafile.path
        if t == 'Source':
            self.filters[i] = self.env.source_plugins[p][0](path)
            self.filters[i].args['fpsnum'] = self.mediafile.fpsnum
            self.filters[i].args['fpsden'] = self.mediafile.fpsden
        elif t == 'Crop':
            self.filters[i] = self.env.crop_plugins[p][0]()
        elif t == 'Resize':
            self.filters[i] = self.env.resize_plugins[p][0]()
            self.filters[i].args['width'] = self.mediafile.width
            self.filters[i].args['height'] = self.mediafile.height
        elif t == 'Denoise':
            self.filters[i] = self.env.denoise_plugins[p][0]()
        elif t == 'Deband':
            self.filters[i] = self.env.deband_plugins[p][0]()
        elif t == 'Misc':
            self.filters[i] = self.env.misc_plugins[p][0]()
            if p == 'Trim':
                self.filters[i].args['first'] = self.mediafile.first
                self.filters[i].args['last'] = self.mediafile.last

        self._populate_grid()

    def on_conf_clicked(self, button, i):
        self.filters[i].show_dialog(self)
        f = self.filters[i]
        if isinstance(f, plugin.SourcePlugin):
            self.mediafile.fpsnum = self.filters[i].args['fpsnum']
            self.mediafile.fpsden = self.filters[i].args['fpsden']
        elif isinstance(f, plugin.ResizePlugin):
            self.mediafile.width = self.filters[i].args['width']
            self.mediafile.height = self.filters[i].args['height']
        elif isinstance(f, plugin.Trim):
            self.mediafile.first = self.filters[i].args['first']
            self.mediafile.last = self.filters[i].args['last']

# vim: ts=4 sw=4 et:
