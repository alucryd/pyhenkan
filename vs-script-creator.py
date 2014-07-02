#!/usr/bin/env python3

import os
from gi.repository import Gtk,GdkPixbuf

class Handler:
    def __init__(self):
        self.cwd = ''
        self.output = 'script.vpy'
        self.source = ''
        self.crop = []
        self.deband = ''
        self.resize = []

    def on_source_set(self, button):
        self.source = button.get_filename()
        self.cwd, self.output = os.path.split(self.source)
        self.output = os.path.splitext(self.output)[0] + '.vpy'
        crop_check.set_sensitive(True)
        resize_check.set_sensitive(True)
        deband_check.set_sensitive(True)
        self.update_script()

    def on_crop_toggled(self, check):
        if check.get_active():
            lcrop_spin.set_sensitive(True)
            rcrop_spin.set_sensitive(True)
            tcrop_spin.set_sensitive(True)
            bcrop_spin.set_sensitive(True)
            self.crop = [lcrop_spin.get_value_as_int(),
                         rcrop_spin.get_value_as_int(),
                         tcrop_spin.get_value_as_int(),
                         bcrop_spin.get_value_as_int()]
        else:
            self.crop = []
            lcrop_spin.set_sensitive(False)
            rcrop_spin.set_sensitive(False)
            tcrop_spin.set_sensitive(False)
            bcrop_spin.set_sensitive(False)
        self.update_script()

    def on_lcrop_changed(self, spin):
        self.crop[0] = spin.get_value_as_int()
        self.update_script()

    def on_rcrop_changed(self, spin):
        self.crop[1] = spin.get_value_as_int()
        self.update_script()

    def on_tcrop_changed(self, spin):
        self.crop[2] = spin.get_value_as_int()
        self.update_script()

    def on_bcrop_changed(self, spin):
        self.crop[3] = spin.get_value_as_int()
        self.update_script()

    def on_resize_toggled(self, check):
        if check.get_active():
            wresize_spin.set_sensitive(True)
            hresize_spin.set_sensitive(True)
            resize_filter_cbtext.set_sensitive(True)
            self.resize = [wresize_spin.get_value_as_int(),
                           hresize_spin.get_value_as_int(),
                           resize_filter_cbtext.get_active_text()]
        else:
            self.resize = []
            wresize_spin.set_sensitive(False)
            hresize_spin.set_sensitive(False)
            resize_filter_cbtext.set_sensitive(False)
        self.update_script()

    def on_wresize_changed(self, spin):
        self.resize[0] = spin.get_value_as_int()
        self.update_script()

    def on_hresize_changed(self, spin):
        self.resize[1] = spin.get_value_as_int()
        self.update_script()

    def on_resize_filter_changed(self, combo):
        self.resize[2] = combo.get_active_text()
        self.update_script()

    def on_deband_toggled(self, check):
        if check.get_active():
            deband_preset_cbtext.set_sensitive(True)
            deband_channel_cbtext.set_sensitive(True)
            deband_nograin_check.set_sensitive(True)
            self.deband_preset()
        else:
            self.deband = ''
            deband_preset_cbtext.set_sensitive(False)
            deband_channel_cbtext.set_sensitive(False)
            deband_nograin_check.set_sensitive(False)
        self.update_script()

    def on_deband_preset_changed(self, combo):
        self.deband_preset()
        self.update_script()

    def on_deband_channel_changed(self, combo):
        self.deband_preset()
        self.update_script()

    def on_deband_nograin_toggled(self, check):
        self.deband_preset()
        self.update_script()

    def deband_preset(self):
        p = deband_preset_cbtext.get_active_text()
        c = deband_channel_cbtext.get_active_text()
        n = deband_nograin_check.get_active()
        self.deband = p
        if c in ['luma', 'chroma']:
            self.deband = '/'.join([self.deband, c])
        if n:
            self.deband = '/'.join([self.deband, 'nograin'])

    def update_script(self):
        # Tried to set up marks to only replace relevant parts, but left or
        # right gravity can't cover all user input cases, marks will always end
        # up in weird places, only choice is to flush the buffer every time.
        s = ''
        c = ''
        d = ''
        r = ''
        script_buffer.set_text("")
        script_buffer.insert_at_cursor("import vapoursynth as vs\n")
        script_buffer.insert_at_cursor("core = vs.get_core()\n")
        s = 'clip = core.ffms2.Source("{}")\n'.format(self.source)
        if self.crop:
            c = 'clip = core.std.CropRel(clip, {}, {}, {}, {})\n'
            c = c.format(self.crop[0], self.crop[1], self.crop[2],
                         self.crop[3])
        if self.deband:
            d = 'clip = core.f3kdb.Deband(clip, preset="{}", '
            d = d + 'output_depth=16)\n'
            d = d.format(self.deband)
        if self.resize:
            r = 'clip = core.resize.{}(clip, {}, {})\n'
            r = r.format(self.resize[2].capitalize(), self.resize[0],
                         self.resize[1])
        script_buffer.insert_at_cursor(s + c + d + r)
        script_buffer.insert_at_cursor("clip.set_output()")

    def on_script_changed(self, buffer):
        save_button.set_sensitive(True)
        preview_button.set_sensitive(True)

    def update_preview(self, frame):
        # Please disregard the following.
        vpy = script_buffer.get_text(script_buffer.get_start_iter(),
                                     script_buffer.get_end_iter(),
                                     include_hidden_chars=True)
        vpy = compile(vpy, '<string>', 'exec')
        preview_ns = {}
        exec(vpy, preview_ns)
        vs = preview_ns['vs']
        core = preview_ns['core']
        clip = preview_ns['clip']
        clip = core.resize.Bicubic(clip, format=vs.COMPATBGR32)
        data = clip.get_frame(frame)
        width = data.width
        height = data.height
        stride = data.get_stride(0)
        pixbuf = GdkPixbuf.Pixbuf.new_from_data(data.get_read_ptr(0),
                                                GdkPixbuf.Colorspace.RGB,
                                                False, 8, width, height,
                                                stride, None, True)
        preview_image.set_from_pixbuf(pixbuf)

    def on_preview_clicked(self, button):
        self.update_preview(0)
        preview_dialog.run()

    def on_save_clicked(self, button):
        save_fcdialog.set_current_folder(self.cwd)
        save_fcdialog.set_current_name(self.output)
        save_fcdialog.run()

    def on_save_ok_clicked(self, button):
        o = save_fcdialog.get_filename()
        vpy = script_buffer.get_text(script_buffer.get_start_iter(),
                                     script_buffer.get_end_iter(),
                                     include_hidden_chars=True)
        with open(o, 'w') as f:
            f.write(vpy)
        save_fcdialog.hide()

    def on_save_cancel_clicked(self, button):
        save_fcdialog.hide()

    def on_window_delete_event(self, *args):
        Gtk.main_quit(*args)

# Build the GUI
builder = Gtk.Builder()
builder.add_from_file('/home/alucryd/pyanimenc/vs-script-creator.glade')

window = builder.get_object('window')
crop_check = builder.get_object('crop-check')
lcrop_spin = builder.get_object('lcrop-spin')
rcrop_spin = builder.get_object('rcrop-spin')
tcrop_spin = builder.get_object('tcrop-spin')
bcrop_spin = builder.get_object('bcrop-spin')
resize_check = builder.get_object('resize-check')
wresize_spin = builder.get_object('wresize-spin')
hresize_spin = builder.get_object('hresize-spin')
resize_filter_cbtext = builder.get_object('resize_filter-cbtext')
deband_check = builder.get_object('deband-check')
deband_preset_cbtext = builder.get_object('deband_preset-cbtext')
deband_channel_cbtext = builder.get_object('deband_channel-cbtext')
deband_nograin_check = builder.get_object('deband_nograin-check')
script_textview = builder.get_object('script-textview')
script_buffer = builder.get_object('script-buffer')
preview_button = builder.get_object('preview-button')
preview_dialog = builder.get_object('preview-dialog')
preview_image = builder.get_object('preview-image')
save_button = builder.get_object('save-button')
save_fcdialog = builder.get_object('save-fcdialog')

handler = Handler()
builder.connect_signals(handler)

window.show_all()

Gtk.main()

# vim: ts=4 sw=4 et:
