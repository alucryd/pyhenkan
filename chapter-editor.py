#!/usr/bin/env python3

import os
import yaml
from gi.repository import Gtk,GdkPixbuf
from pyanimenc import Chapters

class Handler:
    def __init__(self):
        self.cwd = ''
        self.output = 'chapter.xml'
        self.chapters = [["New Chapter", 0, 0, '']]
        self.lang = 'eng'
        self.fpsnum = 24000
        self.fpsden = 1001
        self.ordered = False
        self.update_entries()

    def on_open_clicked(self, button):
        open_fcdialog.run()

    def on_open_ok_clicked(self, button):
        x = open_fcdialog.get_filename()
        with open(x, 'r') as f:
            d = f.read()
        d = yaml.load(d)

        self.cwd, self.output = os.path.split(x)
        self.output = os.path.splitext(self.output)[0] + '.xml'
        self.chapters = d['chapters']
        l = d.get('lang', 'eng')
        lang_entry.set_text(l)
        fn = d.get('fpsnum', 24000)
        fpsnum_spin.set_value(fn)
        fd = d.get('fpsden', 1001)
        fpsden_spin.set_value(fd)
        o = d.get('ordered', False)
        ordered_check.set_active(o)
        self.update_entries()
        open_fcdialog.hide()

    def on_open_cancel_clicked(self, button):
        open_fcdialog.hide()

    def on_save_clicked(self, button):
        save_fcdialog.set_current_folder(self.cwd)
        save_fcdialog.set_current_name(self.output)
        save_fcdialog.run()

    def on_save_ok_clicked(self, button):
        o = save_fcdialog.get_filename()

        c = Chapters(self.lang, self.fpsnum, self.fpsden, self.ordered)
        c = c.chapter(self.chapters)
        with open(o, 'wb') as f:
            f.write(c)

        save_fcdialog.hide()

    def on_save_cancel_clicked(self, button):
        save_fcdialog.hide()

    def on_settings_clicked(self, button):
        settings_dialog.run()

    def on_settings_ok_clicked(self, button):
        settings_dialog.hide()

    def on_ordered_toggled(self, check):
        self.ordered = check.get_active()
        self.update_entries()

    def on_lang_changed(self, entry):
        self.lang = entry.get_text()

    def on_fpsnum_value_changed(self, spin):
        self.fpsnum = spin.get_value_as_int()

    def on_fpsden_value_changed(self, spin):
        self.fpsden = spin.get_value_as_int()

    def update_entries(self):
        # A new builder instance needs to be created for each entry,
        # therefore put the template on its own to avoid loading a large
        # file every time
        for entry in entries_box.get_children():
            entries_box.remove(entry)

        for i in range(len(self.chapters)):
            builder = Gtk.Builder()
            builder.add_from_file('/home/alucryd/pyanimenc/chapter.glade')
            grid = builder.get_object('grid')
            entries_box.pack_start(grid, False, False, 0)
            title = builder.get_object('title-entry')
            title.connect('changed', self.on_title_changed, i)
            start = builder.get_object('start-spin')
            start.connect('value-changed', self.on_start_changed, i)
            end = builder.get_object('end-spin')
            end.connect('value-changed', self.on_end_changed, i)
            end.set_sensitive(self.ordered)
            uid = builder.get_object('uid-entry')
            uid.connect('changed', self.on_uid_changed, i)
            uid.set_sensitive(self.ordered)
            delete = builder.get_object('delete-button')
            delete.connect('clicked', self.on_delete_clicked, i)
            down = builder.get_object('down-button')
            down.connect('clicked', self.on_move_clicked, 'down', i)
            up = builder.get_object('up-button')
            up.connect('clicked', self.on_move_clicked, 'up', i)

            title.set_text(self.chapters[i][0])
            start.set_value(self.chapters[i][1])
            if self.ordered:
                end.set_value(self.chapters[i][2])
            if self.ordered:
                if len(self.chapters[i]) < 4:
                    self.chapters[i].append('')
                uid.set_text(self.chapters[i][3])

            if len(self.chapters) > 1:
                delete.set_sensitive(True)
            if i < len(self.chapters) - 1:
                down.set_sensitive(True)
            if i > 0:
                up.set_sensitive(True)

        window.show()

    def on_new_clicked(self, button):
        self.chapters.append(["New Chapter", 0, 0, ''])
        self.update_entries()

    def on_title_changed(self, entry, i):
        self.chapters[i][0] = entry.get_text()

    def on_start_changed(self, button, i):
        self.chapters[i][1] = button.get_value_as_int()

    def on_end_changed(self, button, i):
        self.chapters[i][2] = button.get_value_as_int()

    def on_uid_changed(self, entry, i):
        self.chapters[i][3] = entry.get_text()

    def on_delete_clicked(self, button, i):
        self.chapters.pop(i)
        self.update_entries()

    def on_move_clicked(self, button, direction, i):
        if direction == 'up':
            self.chapters[i - 1:i + 1] = [self.chapters[i],
                                          self.chapters[i - 1]]
        elif direction == 'down':
            self.chapters[i:i + 2] = [self.chapters[i + 1],
                                      self.chapters[i]]
        self.update_entries()

    def on_window_delete_event(self, *args):
        Gtk.main_quit(*args)

# Build the GUI
builder = Gtk.Builder()
builder.add_from_file('/home/alucryd/pyanimenc/chapter-editor.glade')

window = builder.get_object('window')
entries_box = builder.get_object('entries-box')
open_fcdialog = builder.get_object('open-fcdialog')
save_fcdialog = builder.get_object('save-fcdialog')
settings_dialog = builder.get_object('settings-dialog')
ordered_check = builder.get_object('ordered-check')
lang_entry = builder.get_object('lang-entry')
fpsnum_spin = builder.get_object('fpsnum-spin')
fpsden_spin = builder.get_object('fpsden-spin')

handler = Handler()
builder.connect_signals(handler)

window.show_all()

Gtk.main()

# vim: ts=4 sw=4 et:
