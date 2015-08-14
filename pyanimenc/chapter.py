#!/usr/bin/env python3

from decimal import Decimal
from gi.repository import Gio, Gtk
from lxml import etree
from random import randrange

class Chapters:

    def __init__(self, ordered=False, frame=False, fpsnum=24000, fpsden=1001):
        self.ordered = ordered
        self.frame = frame
        self.fpsnum = fpsnum
        self.fpsden = fpsden

    def frame_to_time(self, frames):
        time = Decimal(frames) * Decimal(self.fpsden) / Decimal(self.fpsnum)
        hours = int(time // 3600)
        minutes = int((time - hours * 3600) // 60)
        seconds = round(time - hours * 3600 - minutes * 60, 3)
        return '{:0>2d}:{:0>2d}:{:0>12.9f}'.format(hours, minutes, seconds)

    def time_to_frame(self, time):
        hours, minutes, seconds = time.split(':')
        s = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        f = round(Decimal(s) * Decimal(self.fpsnum) / Decimal(self.fpsden))

        return f

    def _atom(self, chapter):
        atom = etree.Element('ChapterAtom')
        uid = etree.SubElement(atom, 'ChapterUID')
        uid.text = str(randrange(1000000000))
        if self.ordered:
            seg_uid = etree.SubElement(atom, 'ChapterSegmentUID', format='hex')
            seg_uid.text = chapter[4]
        display = etree.SubElement(atom, 'ChapterDisplay')
        string = etree.SubElement(display, 'ChapterString')
        string.text = chapter[0]
        lang = etree.SubElement(display, 'ChapterLanguage')
        lang.text = chapter[1]
        start = etree.SubElement(atom, 'ChapterTimeStart')
        if self.frame:
            start.text = self.frame_to_time(chapter[2])
        else:
            start.text = chapter[2]
        if self.ordered:
            end = etree.SubElement(atom, 'ChapterTimeEnd')
            if self.frame:
                end.text = self.frame_to_time(chapter[3])
            else:
                end.text = chapter[3]
        return atom

    def build(self, chapters):
        chaps = etree.Element('Chapters')
        edit = etree.SubElement(chaps, 'EditionEntry')
        edit_uid = etree.SubElement(edit, 'EditionUID')
        edit_uid.text = str(randrange(1000000000))
        if self.ordered:
            ordered = etree.SubElement(edit, 'EditionFlagOrdered')
            ordered.text = '1'
        for chapter in chapters:
            c = self._atom(chapter)
            edit.append(c)
        doctype = '<!-- <!DOCTYPE Chapters SYSTEM "matroskachapters.dtd"> -->'
        xml = etree.tostring(chaps, encoding='UTF-8', pretty_print=True,
                             xml_declaration=True, doctype=doctype)
        return xml

    def parse(self, xml):
        ordered = False
        chapters = []
        root = etree.fromstring(xml)

        for child in root[0]:
            if child.tag == 'EditionFlagOrdered' and child.text == '1':
                ordered = True
            elif child.tag == 'ChapterAtom':
                title = ''
                lang = 'und'
                start = '00:00:00.000000000'
                end = '00:00:00.000000000'
                uid = ''
                for gchild in child:
                    if gchild.tag == 'ChapterSegmentUID' and gchild.text:
                        uid = gchild.text
                    elif gchild.tag == 'ChapterTimeStart':
                        start = gchild.text
                    elif gchild.tag == 'ChapterTimeEnd':
                        end = gchild.text
                    elif gchild.tag == 'ChapterDisplay':
                        for ggchild in gchild:
                            if ggchild.tag == 'ChapterString':
                                title = ggchild.text
                            elif ggchild.tag == 'ChapterLanguage':
                                lang = ggchild.text

                chapters.append([title, lang, start, end, uid])

        return (ordered, chapters)

class ChapterEditorWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title='pyanimchap')
        self.set_default_size(640, 0)

        self.lang = 'und'
        self.ordered = False
        self.frame = False
        self.fpsnum = 24000
        self.fpsden = 1001
        self.chapters = [['Chapter 1', self.lang, '00:00:00.000000000',
                          '00:00:00.000000000', ''],
                         ['Chapter 2', self.lang, '00:00:00.000000000',
                          '00:00:00.000000000', ''],
                         ['Chapter 3', self.lang, '00:00:00.000000000',
                          '00:00:00.000000000', '']]

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vport = Gtk.Viewport()
        vport.add(self.box)
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.add(vport)
        self.add(self.scrwin)

        #--Header Bar--#
        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.set_property('title', 'pyanimchap')

        open_button = Gtk.Button('Open')
        open_button.connect('clicked', self.on_open_clicked)
        save_button = Gtk.Button('Save')
        save_button.connect('clicked', self.on_save_clicked)

        settings_popover = Gtk.Popover()
        settings_mbutton = Gtk.MenuButton()
        settings_icon = Gio.ThemedIcon(name='applications-system-symbolic')
        settings_image = Gtk.Image.new_from_gicon(settings_icon,
                                                  Gtk.IconSize.BUTTON)
        settings_mbutton.set_image(settings_image)
        settings_mbutton.set_direction(Gtk.ArrowType.DOWN)
        settings_mbutton.set_use_popover(True)
        settings_mbutton.set_popover(settings_popover)

        add_button = Gtk.Button()
        add_icon = Gio.ThemedIcon(name='list-add-symbolic')
        add_image = Gtk.Image.new_from_gicon(add_icon, Gtk.IconSize.BUTTON)
        add_button.set_image(add_image)
        add_button.connect('clicked', self.on_add_clicked)

        hbar.pack_start(open_button)
        hbar.pack_start(save_button)
        hbar.pack_end(settings_mbutton)
        hbar.pack_end(add_button)

        self.set_titlebar(hbar)

        #--Open/Save--#
        cflt = Gtk.FileFilter()
        cflt.set_name('XML Chapter')
        cflt.add_pattern('*.xml')
        self.open_fcdlg = Gtk.FileChooserDialog('Open chapters', self,
                                                Gtk.FileChooserAction.OPEN,
                                                ('Cancel',
                                                 Gtk.ResponseType.CANCEL,
                                                 'Open', Gtk.ResponseType.OK))
        self.open_fcdlg.add_filter(cflt)
        self.save_fcdlg = Gtk.FileChooserDialog('Save chapters', self,
                                                Gtk.FileChooserAction.SAVE,
                                                ('Cancel',
                                                 Gtk.ResponseType.CANCEL,
                                                 'Save', Gtk.ResponseType.OK))
        self.save_fcdlg.add_filter(cflt)

        #--Settings--#
        settings_grid = Gtk.Grid()
        settings_grid.set_property('margin', 6)
        settings_grid.set_column_spacing(6)
        settings_grid.set_row_spacing(6)

        lang_label = Gtk.Label('Language')
        lang_entry = Gtk.Entry()
        lang_entry.set_property('hexpand', True)
        lang_entry.set_max_length(3)
        lang_entry.set_max_width_chars(3)
        lang_entry.set_text(self.lang)
        lang_entry.connect('changed', self.on_lang_changed, -1)

        ordered_label = Gtk.Label('Ordered')
        ordered_check = Gtk.CheckButton()
        ordered_check.set_active(self.ordered)
        ordered_check.connect('toggled', self.on_ordered_toggled)

        input_label = Gtk.Label('Input')
        input_cbtext = Gtk.ComboBoxText()
        input_cbtext.append_text('Timecode')
        input_cbtext.append_text('Frame')
        input_cbtext.set_active(0)
        input_cbtext.connect('changed', self.on_input_changed)

        fps_label = Gtk.Label('FPS')
        fpsnum_adj = Gtk.Adjustment(24000, 1, 300000, 1, 10)
        fpsnum_spin = Gtk.SpinButton()
        fpsnum_spin.set_numeric(True)
        fpsnum_spin.set_adjustment(fpsnum_adj)
        fpsnum_spin.set_property('hexpand', True)
        fpsnum_spin.set_value(self.fpsnum)
        fpsden_adj = Gtk.Adjustment(1001, 1, 1001, 1, 1)
        fpsden_spin = Gtk.SpinButton()
        fpsden_spin.set_numeric(True)
        fpsden_spin.set_adjustment(fpsden_adj)
        fpsden_spin.set_property('hexpand', True)
        fpsden_spin.set_value(self.fpsden)

        settings_grid.attach(lang_label, 0, 0, 1, 1)
        settings_grid.attach(lang_entry, 1, 0, 1, 1)
        settings_grid.attach(ordered_label, 0, 1, 1, 1)
        settings_grid.attach(ordered_check, 1, 1, 1, 1)
        settings_grid.attach(input_label, 0, 2, 1, 1)
        settings_grid.attach(input_cbtext, 1, 2, 1, 1)
        settings_grid.attach(fps_label, 0, 3, 1, 2)
        settings_grid.attach(fpsnum_spin, 1, 3, 1, 1)
        settings_grid.attach(fpsden_spin, 1, 4, 1, 1)

        settings_grid.show_all()
        settings_popover.add(settings_grid)

        #--Entries--#
        self._update_entries()

    def _update_entries(self):
        for child in self.box.get_children():
            self.box.remove(child)

        for i in range(len(self.chapters)):
            grid = Gtk.Grid()
            grid.set_column_spacing(6)
            grid.set_row_spacing(6)
            grid.set_property('margin', 6)

            title_label = Gtk.Label('Title')
            title_entry = Gtk.Entry()
            title_entry.set_property('hexpand', True)
            title_entry.set_text(self.chapters[i][0])
            title_entry.connect('changed', self.on_title_changed, i)

            lang_label = Gtk.Label('Language')
            lang_entry = Gtk.Entry()
            lang_entry.set_property('hexpand', True)
            lang_entry.set_max_length(3)
            lang_entry.set_max_width_chars(3)
            lang_entry.set_text(self.chapters[i][1])
            lang_entry.connect('changed', self.on_lang_changed, i)

            start_label = Gtk.Label('Start')
            end_label = Gtk.Label('End')

            uid_label = Gtk.Label('UID')
            uid_entry = Gtk.Entry()
            uid_entry.set_property('hexpand', True)
            uid_entry.set_sensitive(self.ordered)
            uid_entry.set_text(self.chapters[i][4])
            uid_entry.connect('changed', self.on_uid_changed, i)

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

            grid.attach(title_label, 0, 0, 1, 1)
            grid.attach(title_entry, 1, 0, 1, 1)
            grid.attach(lang_label, 2, 0, 1, 1)
            grid.attach(lang_entry, 3, 0, 1, 1)
            grid.attach(up_button, 4, 0, 1, 1)
            grid.attach(start_label, 0, 1, 1, 1)
            grid.attach(end_label, 2, 1, 1, 1)
            grid.attach(remove_button, 4, 1, 1, 1)
            grid.attach(uid_label, 0, 2, 1, 1)
            grid.attach(uid_entry, 1, 2, 3, 1)
            grid.attach(down_button, 4, 2, 1, 1)

            if self.frame:
                start_adj = Gtk.Adjustment(0, 0, 256000, 1, 10)
                start_spin = Gtk.SpinButton()
                start_spin.set_numeric(True)
                start_spin.set_adjustment(start_adj)
                start_spin.set_property('hexpand', True)
                start_spin.set_value(self.chapters[i][2])
                start_spin.connect('value-changed', self.on_start_changed, i)

                end_adj = Gtk.Adjustment(0, 0, 256000, 1, 10)
                end_spin = Gtk.SpinButton()
                end_spin.set_numeric(True)
                end_spin.set_adjustment(end_adj)
                end_spin.set_property('hexpand', True)
                end_spin.set_sensitive(self.ordered)
                end_spin.set_value(self.chapters[i][3])
                end_spin.connect('value-changed', self.on_end_changed, i)

                grid.attach(start_spin, 1, 1, 1, 1)
                grid.attach(end_spin, 3, 1, 1, 1)

            else:
                start_entry = Gtk.Entry()
                start_entry.set_property('hexpand', True)
                start_entry.set_max_length(18)
                start_entry.set_max_width_chars(18)
                start_entry.set_text(self.chapters[i][2])
                start_entry.connect('changed', self.on_start_changed, i)

                end_entry = Gtk.Entry()
                end_entry.set_property('hexpand', True)
                end_entry.set_max_length(18)
                end_entry.set_max_width_chars(18)
                end_entry.set_sensitive(self.ordered)
                end_entry.set_text(self.chapters[i][3])
                end_entry.connect('changed', self.on_end_changed, i)

                grid.attach(start_entry, 1, 1, 1, 1)
                grid.attach(end_entry, 3, 1, 1, 1)

            if len(self.chapters) == 1:
                remove_button.set_sensitive(False)
            if i == 0:
                up_button.set_sensitive(False)
            if i == len(self.chapters) - 1:
                down_button.set_sensitive(False)

            self.box.pack_start(grid, False, True, 0)


        if len(self.chapters) <= 3:
            self.scrwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
            self.resize(640, 1)
        else:
            self.scrwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)

        self.show_all()

    def on_open_clicked(self, button):
        response = self.open_fcdlg.run()

        if response == Gtk.ResponseType.OK:
            i = self.open_fcdlg.get_filename()

            with open(i, 'rb') as f:
                xml = f.read()

            c = Chapters(self.ordered, self.frame, self.fpsnum, self.fpsden)
            self.ordered, self.chapters = c.parse(xml)
            # Entries will be updated 2 times if self.ordered changes, find a
            # way around that later
            self._update_entries()

        self.open_fcdlg.hide()

    def on_save_clicked(self, button):
        response = self.save_fcdlg.run()

        if response == Gtk.ResponseType.OK:
            o = self.save_fcdlg.get_filename()
            if not re.search('\.xml$', o):
                o = o + '.xml'
            c = Chapters(self.ordered, self.frame, self.fpsnum, self.fpsden)
            c = c.build(self.chapters)

            with open(o, 'wb') as f:
                f.write(c)

        self.save_fcdlg.hide()

    def on_add_clicked(self, button):
        if self.frame:
            self.chapters.append(['Chapter ' + str(len(self.chapters) + 1),
                                  self.lang, 0, 0, ''])
        else:
            self.chapters.append(['Chapter ' + str(len(self.chapters) + 1),
                                  self.lang, '00:00:00.000000000',
                                  '00:00:00.000000000', ''])

        self._update_entries()

    def on_remove_clicked(self, button, i):
        self.chapters.pop(i)
        self._update_entries()

    def on_move_clicked(self, button, direction, i):
        if direction == 'up':
            self.chapters[i - 1:i + 1] = [self.chapters[i],
                                          self.chapters[i - 1]]
        elif direction == 'down':
            self.chapters[i:i + 2] = [self.chapters[i + 1],
                                      self.chapters[i]]
        self._update_entries()

    def on_ordered_toggled(self, check):
        self.ordered = check.get_active()
        self._update_entries()

    def on_input_changed(self, cbtext):
        if cbtext.get_active_text() == 'Frame':
            self.frame = True
        else:
            self.frame = False

        c = Chapters(self.ordered, self.frame, self.fpsnum, self.fpsden)
        for chapter in self.chapters:
            if self.frame:
                chapter[2] = c.time_to_frame(chapter[2])
                chapter[3] = c.time_to_frame(chapter[3])
            else:
                chapter[2] = c.frame_to_time(chapter[2])
                chapter[3] = c.frame_to_time(chapter[3])

        self._update_entries()

    def on_title_changed(self, entry, i):
        self.chapters[i][0] = entry.get_text()

    def on_lang_changed(self, entry, i):
        if i < 0:
            self.lang = entry.get_text()
            for chapter in self.chapters:
                chapter[1] = self.lang
                self._update_entries()
        else:
            self.chapters[i][1] = entry.get_text()

    def on_start_changed(self, widget, i):
        if self.frame:
            self.chapters[i][2] = widget.get_value_as_int()
        else:
            self.chapters[i][2] = widget.get_text()

    def on_end_changed(self, widget, i):
        if self.frame:
            self.chapters[i][3] = widget.get_value_as_int()
        else:
            self.chapters[i][3] = widget.get_text()

    def on_uid_changed(self, entry, i):
        self.chapters[i][4] = entry.get_text()

# vim: ts=4 sw=4 et:
