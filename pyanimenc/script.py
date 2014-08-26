#!/usr/bin/env python3

import os
from gi.repository import Gtk,GdkPixbuf
from pkg_resources import resource_string
from pyanimenc.helpers import Encode

# Main UI
builder = Gtk.Builder()
script_glade = resource_string(__name__, 'glade/script.glade')
script_glade = script_glade.decode('utf8')
builder.add_from_string(script_glade)
filters_glade = resource_string(__name__, 'glade/filters.glade')
filters_glade = filters_glade.decode('utf8')
builder.add_from_string(filters_glade)

window = builder.get_object('window')
open_fcdialog = builder.get_object('open-fcdialog')
save_button = builder.get_object('save-button')
save_fcdialog = builder.get_object('save-fcdialog')
params_button = builder.get_object('params-button')
params_fcdialog = builder.get_object('params-fcdialog')
preview_button = builder.get_object('preview-button')
preview_dialog = builder.get_object('preview-dialog')
preview_image = builder.get_object('preview-image')
script_textview = builder.get_object('script-textview')
script_buffer = builder.get_object('script-buffer')

# VapourSynth UI
vpy_dialog = builder.get_object('vpy-dialog')
fps_check = builder.get_object('fps-check')
fpsnum_spin = builder.get_object('fpsnum-spin')
fpsden_spin = builder.get_object('fpsden-spin')
crop_check = builder.get_object('crop-check')
lcrop_spin = builder.get_object('lcrop-spin')
rcrop_spin = builder.get_object('rcrop-spin')
tcrop_spin = builder.get_object('tcrop-spin')
bcrop_spin = builder.get_object('bcrop-spin')
resize_check = builder.get_object('resize-check')
wresize_spin = builder.get_object('wresize-spin')
hresize_spin = builder.get_object('hresize-spin')
resize_algo_cbtext = builder.get_object('resize_algo-cbtext')

sdenoise_check = builder.get_object('sdenoise-check')
sdenoise_cbtext = builder.get_object('sdenoise-cbtext')
sdenoise_conf_button = builder.get_object('sdenoise_conf-button')
rgvs_dialog = builder.get_object('rgvs-dialog')
rgvs_mode_spin = builder.get_object('rgvs_mode-spin')
rgvs_adv_check = builder.get_object('rgvs_adv-check')
rgvs_umode_spin = builder.get_object('rgvs_umode-spin')
rgvs_vmode_spin = builder.get_object('rgvs_vmode-spin')
rgvs_ok_button = builder.get_object('rgvs_ok-button')

tdenoise_check = builder.get_object('tdenoise-check')
tdenoise_cbtext = builder.get_object('tdenoise-cbtext')
tdenoise_conf_button = builder.get_object('tdenoise_conf-button')
tsoft_dialog = builder.get_object('tsoft-dialog')
tsoft_rad_spin = builder.get_object('tsoft_rad-spin')
tsoft_lt_spin = builder.get_object('tsoft_lt-spin')
tsoft_ct_spin = builder.get_object('tsoft_ct-spin')
tsoft_sc_spin = builder.get_object('tsoft_sc-spin')
tsoft_ok_button = builder.get_object('tsoft_ok-button')

stdenoise_check = builder.get_object('stdenoise-check')
stdenoise_cbtext = builder.get_object('stdenoise-cbtext')
stdenoise_conf_button = builder.get_object('stdenoise_conf-button')
fsmooth_dialog = builder.get_object('fsmooth-dialog')
fsmooth_tt_spin = builder.get_object('fsmooth_tt-spin')
fsmooth_st_spin = builder.get_object('fsmooth_st-spin')
fsmooth_yplane_check = builder.get_object('fsmooth_yplane-check')
fsmooth_uplane_check = builder.get_object('fsmooth_uplane-check')
fsmooth_vplane_check = builder.get_object('fsmooth_vplane-check')
fsmooth_ok_button = builder.get_object('fsmooth_ok-button')

deband_check = builder.get_object('deband-check')
deband_cbtext = builder.get_object('deband-cbtext')
deband_conf_button = builder.get_object('deband_conf-button')
f3kdb_dialog = builder.get_object('f3kdb-dialog')
f3kdb_preset_cbtext = builder.get_object('f3kdb_preset-cbtext')
f3kdb_planes_cbtext = builder.get_object('f3kdb_planes-cbtext')
f3kdb_grain_check = builder.get_object('f3kdb_grain-check')
f3kdb_depth_spin = builder.get_object('f3kdb_depth-spin')
f3kdb_ok_button = builder.get_object('f3kdb_ok-button')

class Handler:
    def __init__(self):
        self.source = ''

    def on_open_clicked(self, button):
        open_fcdialog.run()

    def on_open_ok_clicked(self, button):
        self.source = open_fcdialog.get_filename()
        save_button.set_sensitive(True)
        params_button.set_sensitive(True)
        open_fcdialog.hide()
        self.update_script()

    def on_open_cancel_clicked(self, button):
        open_fcdialog.hide()

    def on_save_clicked(self, button):
        wd = os.path.dirname(self.source)
        o = os.path.basename(self.source)
        o = os.path.splitext(o)[0] + '.vpy'
        save_fcdialog.set_current_folder(wd)
        save_fcdialog.set_current_name(o)
        save_fcdialog.run()

    def on_save_ok_clicked(self, button):
        o = save_fcdialog.get_filename()
        s = script_buffer.get_text(script_buffer.get_start_iter(),
                                   script_buffer.get_end_iter(),
                                   include_hidden_chars=True)
        with open(o, 'w') as f:
            f.write(s)
        save_fcdialog.hide()

    def on_save_cancel_clicked(self, button):
        save_fcdialog.hide()

    def on_params_clicked(self, button):
        vpy_dialog.run()

    def on_vpy_ok_clicked(self, button):
        self.update_script()
        vpy_dialog.hide()

    def on_fps_toggled(self, check):
        state = check.get_active()
        fpsnum_spin.set_sensitive(state)
        fpsden_spin.set_sensitive(state)

    def on_crop_toggled(self, check):
        state = check.get_active()
        lcrop_spin.set_sensitive(state)
        rcrop_spin.set_sensitive(state)
        tcrop_spin.set_sensitive(state)
        bcrop_spin.set_sensitive(state)

    def on_resize_toggled(self, check):
        state = check.get_active()
        wresize_spin.set_sensitive(state)
        hresize_spin.set_sensitive(state)
        resize_algo_cbtext.set_sensitive(state)

    def on_sdenoise_toggled(self, check):
        state = check.get_active()
        sdenoise_cbtext.set_sensitive(state)
        sdenoise_conf_button.set_sensitive(state)

    def on_sdenoise_conf_clicked(self, button):
        f = sdenoise_cbtext.get_active_text()
        if f == 'RemoveGrain':
            rgvs_dialog.run()

    def on_tdenoise_toggled(self, check):
        state = check.get_active()
        tdenoise_cbtext.set_sensitive(state)
        tdenoise_conf_button.set_sensitive(state)

    def on_tdenoise_conf_clicked(self, button):
        f = tdenoise_cbtext.get_active_text()
        if f == 'TemporalSoften':
            tsoft_dialog.run()
        elif f == 'FluxSmoothT':
            fsmooth_st_spin.set_sensitive(False)
            fsmooth_dialog.run()

    def on_stdenoise_toggled(self, check):
        state = check.get_active()
        stdenoise_cbtext.set_sensitive(state)
        stdenoise_conf_button.set_sensitive(state)

    def on_stdenoise_conf_clicked(self, button):
        f = stdenoise_cbtext.get_active_text()
        if f == 'FluxSmoothST':
            fsmooth_st_spin.set_sensitive(True)
            fsmooth_dialog.run()

    def on_rgvs_adv_toggled(self, check):
        state = check.get_active()
        rgvs_umode_spin.set_sensitive(state)
        rgvs_vmode_spin.set_sensitive(state)

    def on_rgvs_ok_clicked(self, button):
        rgvs_dialog.hide()

    def on_tsoft_ok_clicked(self, button):
        tsoft_dialog.hide()

    def on_fsmooth_ok_clicked(self, button):
        fsmooth_dialog.hide()

    def on_deband_toggled(self, check):
        state = check.get_active()
        deband_cbtext.set_sensitive(state)
        deband_conf_button.set_sensitive(state)

    def on_deband_conf_clicked(self, button):
        f = deband_cbtext.get_active_text()
        if f == 'f3kdb':
            f3kdb_dialog.run()

    def on_f3kdb_ok_clicked(self, button):
        f3kdb_dialog.hide()

    def on_preview_clicked(self, button):
        self.update_preview(0)
        preview_dialog.run()

    def update_script(self):
        # Tried to set up marks to only replace relevant parts, but left or
        # right gravity can't cover all user input cases, marks will always end
        # up in weird places, only choice is to flush the buffer every time.
        fps = []
        if fps_check.get_active():
            fn = fpsnum_spin.get_value_as_int()
            fd = fpsden_spin.get_value_as_int()
            fps = [fn, fd]
        crop = []
        if crop_check.get_active():
            cl = lcrop_spin.get_value_as_int()
            cr = rcrop_spin.get_value_as_int()
            ct = tcrop_spin.get_value_as_int()
            cb = bcrop_spin.get_value_as_int()
            crop = [cl, cr, ct, cb]
        resize = []
        if resize_check.get_active():
            rw = wresize_spin.get_value_as_int()
            rh = hresize_spin.get_value_as_int()
            rf = resize_algo_cbtext.get_active_text()
            resize = [rw, rh, rf]
        sdenoise = []
        if sdenoise_check.get_active():
            sdf = sdenoise_cbtext.get_active_text()
            if sdf == 'RemoveGrain':
                rgm = [rgvs_mode_spin.get_value_as_int()]
                if rgvs_adv_check.get_active():
                    rgm.append(rgvs_umode_spin.get_value_as_int())
                    rgm.append(rgvs_vmode_spin.get_value_as_int())
                sdenoise = [sdf, rgm]
        tdenoise = []
        if tdenoise_check.get_active():
            tdf = tdenoise_cbtext.get_active_text()
            if tdf == 'TemporalSoften':
                tsr = tsoft_rad_spin.get_value_as_int()
                tsl = tsoft_lt_spin.get_value_as_int()
                tsc = tsoft_ct_spin.get_value_as_int()
                tss = tsoft_sc_spin.get_value_as_int()
                tdenoise = [tdf, tsr, tsl, tsc, tss]
            elif tdf == 'FluxSmoothT':
                fst = fsmooth_tt_spin.get_value_as_int()
                fsp = []
                if fsmooth_yplane_check.get_active():
                    fsp.append(0)
                if fsmooth_uplane_check.get_active():
                    fsp.append(1)
                if fsmooth_vplane_check.get_active():
                    fsp.append(2)
                tdenoise = [tdf, fst, fsp]
        stdenoise = []
        if stdenoise_check.get_active():
            stdf = stdenoise_cbtext.get_active_text()
            if stdf == 'FluxSmoothST':
                fst = fsmooth_tt_spin.get_value_as_int()
                fss = fsmooth_st_spin.get_value_as_int()
                fsp = []
                if fsmooth_yplane_check.get_active():
                    fsp.append(0)
                if fsmooth_uplane_check.get_active():
                    fsp.append(1)
                if fsmooth_vplane_check.get_active():
                    fsp.append(2)
                stdenoise = [stdf, fst, fss, fsp]
        deband = []
        if deband_check.get_active():
            df = deband_cbtext.get_active_text()
            if df == 'f3kdb':
                fpr = f3kdb_preset_cbtext.get_active_text()
                fpl = f3kdb_planes_cbtext.get_active_text()
                fdp = f3kdb_depth_spin.get_value_as_int()
                if fpl in ['luma', 'chroma']:
                    fpr = fpr + '/' + fpl
                if not f3kdb_grain_check.get_active():
                    fpr = fpr + '/nograin'
                deband = [df, fpr, fdp]
        s = Encode(self.source).vpy(fps, crop, resize, sdenoise, tdenoise,
                                    stdenoise, deband)
        script_buffer.set_text(s)

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

    def on_window_delete_event(self, *args):
        Gtk.main_quit(*args)

handler = Handler()
builder.connect_signals(handler)

window.show_all()

Gtk.main()

# vim: ts=4 sw=4 et:
