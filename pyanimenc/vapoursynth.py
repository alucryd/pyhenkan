#!/usr/bin/env python3

import pyanimenc.conf as conf
from collections import OrderedDict
from gi.repository import Gio, Gtk
from pyanimenc.filters import FilterDialog

class VapourSynthDialog(Gtk.Dialog):

    def __init__(self, parent):
        Gtk.Dialog.__init__(self, 'VapourSynth settings', parent, 0,
                            use_header_bar=1)

        add_button = Gtk.Button()
        add_icon = Gio.ThemedIcon(name='list-add-symbolic')
        add_image = Gtk.Image.new_from_gicon(add_icon, Gtk.IconSize.BUTTON)
        add_button.set_image(add_image)
        add_button.connect('clicked', self.on_add_clicked)

        hbar = self.get_header_bar()
        hbar.pack_start(add_button)

        self.box = self.get_content_area()

        self._update_filters()

    def _update_filters(self):
        for child in self.box.get_children():
            self.box.remove(child)

        grid = Gtk.Grid()
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        grid.set_property('margin', 6)

        for i in range(len(conf.vs)):
            active_type = conf.vs[i][0]
            active_name = conf.vs[i][1]

            type_cbtext = Gtk.ComboBoxText()
            type_cbtext.set_property('hexpand', True)
            name_cbtext = Gtk.ComboBoxText()
            name_cbtext.set_property('hexpand', True)

            conf_icon = Gio.ThemedIcon(name='applications-system-symbolic')
            conf_image = Gtk.Image.new_from_gicon(conf_icon,
                                                  Gtk.IconSize.BUTTON)
            conf_button = Gtk.Button()
            conf_button.set_image(conf_image)
            conf_button.set_sensitive(False)

            up_button = Gtk.Button()
            up_icon = Gio.ThemedIcon(name='go-up-symbolic')
            up_image = Gtk.Image.new_from_gicon(up_icon, Gtk.IconSize.BUTTON)
            up_button.set_image(up_image)

            down_button = Gtk.Button()
            down_icon = Gio.ThemedIcon(name='go-down-symbolic')
            down_image = Gtk.Image.new_from_gicon(down_icon,
                                                  Gtk.IconSize.BUTTON)
            down_button.set_image(down_image)

            remove_button = Gtk.Button()
            remove_icon = Gio.ThemedIcon(name='list-remove-symbolic')
            remove_image = Gtk.Image.new_from_gicon(remove_icon,
                                                    Gtk.IconSize.BUTTON)
            remove_button.set_image(remove_image)

            j = 0
            for filter_type in conf.FILTERS:
                type_cbtext.append_text(filter_type)

                if active_type == filter_type:
                    type_cbtext.set_active(j)

                    k = 0
                    for filter_name in conf.FILTERS[filter_type]:
                        name_cbtext.append_text(filter_name)

                        if active_name == filter_name:
                            name_cbtext.set_active(k)
                            conf_button.set_sensitive(True)

                        k = k + 1
                j = j + 1

            if i == 0:
                type_cbtext.set_sensitive(False)
                up_button.set_sensitive(False)
                down_button.set_sensitive(False)
                remove_button.set_sensitive(False)
            elif i == 1:
                up_button.set_sensitive(False)

            if i == len(conf.vs) - 1:
                down_button.set_sensitive(False)

            if i > 0:
                type_cbtext.remove(0)

            grid.attach(type_cbtext, 0, i, 1, 1)
            grid.attach(name_cbtext, 1, i, 1, 1)
            grid.attach(conf_button, 2, i, 1, 1)
            grid.attach(up_button, 3, i, 1, 1)
            grid.attach(down_button, 4, i, 1, 1)
            grid.attach(remove_button, 5, i, 1, 1)

            type_cbtext.connect('changed', self.on_type_changed, i)
            name_cbtext.connect('changed', self.on_name_changed, active_type,
                                i)
            conf_button.connect('clicked', self.on_conf_clicked, active_type,
                                active_name, i)
            up_button.connect('clicked', self.on_move_clicked, 'up', i)
            down_button.connect('clicked', self.on_move_clicked, 'down', i)
            remove_button.connect('clicked', self.on_remove_clicked, i)

        self.box.pack_start(grid, True, True, 0)

        self.show_all()

    def on_add_clicked(self, button):
        conf.vs.append(['', '', None])

        self._update_filters()

    def on_remove_clicked(self, button, i):
        conf.vs.pop(i)

        self._update_filters()

    def on_move_clicked(self, button, direction, i):
        if direction == 'up':
            conf.vs[i - 1:i + 1] = [conf.vs[i],
                                       conf.vs[i - 1]]
        elif direction == 'down':
            conf.vs[i:i + 2] = [conf.vs[i + 1],
                                   conf.vs[i]]
        self._update_filters()

    def on_type_changed(self, combo, i):
        t = combo.get_active_text()
        conf.vs[i][0] = t
        conf.vs[i][1] = ''
        conf.vs[i][2] = None

        self._update_filters()

    def on_name_changed(self, combo, t, i):
        n = combo.get_active_text()
        conf.vs[i][0] = t
        conf.vs[i][1] = n
        args = OrderedDict()
        if t == 'Resize':
            args['width'] = 0
            args['height'] = 0
        elif n == 'RemoveGrain':
            args['mode'] = [2]
        elif n == 'Trim':
            args['first'] = 0
            args['last'] = 0
        conf.vs[i][2] = args

        self._update_filters()

    def on_conf_clicked(self, button, t, n, i):
        if t in ['Source', 'Resize']:
            dlg = FilterDialog(self, t, i)
        else:
            dlg = FilterDialog(self, n, i)
        dlg.run()
        dlg.destroy()

# vim: ts=4 sw=4 et:
