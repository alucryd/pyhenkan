#!/usr/bin/env python3

import pyanimenc.conf as conf

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class FilterDialog(Gtk.Dialog):
    def __init__(self, parent, flt, i):
        Gtk.Dialog.__init__(self, flt + ' settings', parent, 0,
                            use_header_bar=True)
        self.set_default_size(240, 0)

        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(6)
        self.grid.set_row_spacing(6)
        self.grid.set_property('margin', 6)

        box = self.get_content_area()
        box.add(self.grid)

        if flt == 'Source':
            self._source()
            self.connect('delete-event', self._update_source)
        elif flt == 'CropAbs':
            self._crop(True, i)
            self.connect('delete-event', self._update_crop, True, i)
        elif flt == 'CropRel':
            self._crop(False, i)
            self.connect('delete-event', self._update_crop, False, i)
        elif flt == 'Resize':
            self._resize(i)
            self.connect('delete-event', self._update_resize, i)
        elif flt == 'FluxSmoothT':
            self._fsmooth(False, i)
            self.connect('delete-event', self._update_fsmooth, False, i)
        elif flt == 'FluxSmoothST':
            self._fsmooth(True, i)
            self.connect('delete-event', self._update_fsmooth, True, i)
        elif flt == 'RemoveGrain':
            self._rgvs(i)
            self.connect('delete-event', self._update_rgvs, i)
        elif flt == 'TemporalSoften':
            self._tsoft(i)
            self.connect('delete-event', self._update_tsoft, i)
        elif flt == 'f3kdb':
            self._f3kdb(i)
            self.connect('delete-event', self._update_f3kdb, i)
        elif flt == 'Trim':
            self._trim(i)
            self.connect('delete-event', self._update_trim, i)

        self.show_all()

    def _source(self):
        fpsnum_adj = Gtk.Adjustment(0, 0, 300000, 1, 100)
        fpsden_adj = Gtk.Adjustment(1, 1, 300000, 1, 100)

        fpsnum_label = Gtk.Label('FPS Numerator')
        fpsnum_label.set_halign(Gtk.Align.START)
        fpsden_label = Gtk.Label('FPS Denominator')
        fpsden_label.set_halign(Gtk.Align.START)

        self.fpsnum_spin = Gtk.SpinButton()
        self.fpsnum_spin.set_adjustment(fpsnum_adj)
        self.fpsnum_spin.set_numeric(True)
        self.fpsnum_spin.set_property('hexpand', True)
        self.fpsden_spin = Gtk.SpinButton()
        self.fpsden_spin.set_adjustment(fpsden_adj)
        self.fpsden_spin.set_numeric(True)
        self.fpsden_spin.set_property('hexpand', True)

        flt = conf.filters[0][2]
        self.fpsnum_spin.set_value(flt.get('fpsnum', 0))
        self.fpsden_spin.set_value(flt.get('fpsden', 1))

        self.grid.attach(fpsnum_label, 0, 0, 1, 1)
        self.grid.attach(self.fpsnum_spin, 1, 0, 1, 1)
        self.grid.attach(fpsden_label, 0, 1, 1, 1)
        self.grid.attach(self.fpsden_spin, 1, 1, 1, 1)

    def _update_source(self, widget, event):
        flt = conf.filters[0][2]

        n = self.fpsnum_spin.get_value_as_int()
        d = self.fpsden_spin.get_value_as_int()

        if n != 0 or d != 1:
            flt['fpsnum'] = n
            flt['fpsden'] = d
            conf.video['fpsnum'] = n
            conf.video['fpsden'] = d

    def _crop(self, absolute, i):
        left_adj = Gtk.Adjustment(0, 0, 3840, 1, 10)
        right_adj = Gtk.Adjustment(0, 0, 3840, 1, 10)
        top_adj = Gtk.Adjustment(0, 0, 2160, 1, 10)
        bottom_adj = Gtk.Adjustment(0, 0, 2160, 1, 10)
        width_adj = Gtk.Adjustment(0, 0, 3840, 1, 10)
        height_adj = Gtk.Adjustment(0, 0, 2160, 1, 10)

        left_label = Gtk.Label('Left')
        left_label.set_halign(Gtk.Align.START)
        right_label = Gtk.Label('Right')
        right_label.set_halign(Gtk.Align.START)
        top_label = Gtk.Label('Top')
        top_label.set_halign(Gtk.Align.START)
        bottom_label = Gtk.Label('Bottom')
        bottom_label.set_halign(Gtk.Align.START)
        width_label = Gtk.Label('Width')
        width_label.set_halign(Gtk.Align.START)
        height_label = Gtk.Label('Height')
        height_label.set_halign(Gtk.Align.START)

        self.left_spin = Gtk.SpinButton()
        self.left_spin.set_adjustment(left_adj)
        self.left_spin.set_numeric(True)
        self.left_spin.set_property('hexpand', True)
        self.right_spin = Gtk.SpinButton()
        self.right_spin.set_adjustment(right_adj)
        self.right_spin.set_numeric(True)
        self.right_spin.set_property('hexpand', True)
        self.right_spin.set_sensitive(not absolute)
        self.top_spin = Gtk.SpinButton()
        self.top_spin.set_adjustment(top_adj)
        self.top_spin.set_numeric(True)
        self.top_spin.set_property('hexpand', True)
        self.bottom_spin = Gtk.SpinButton()
        self.bottom_spin.set_adjustment(bottom_adj)
        self.bottom_spin.set_numeric(True)
        self.bottom_spin.set_property('hexpand', True)
        self.bottom_spin.set_sensitive(not absolute)
        self.width_spin = Gtk.SpinButton()
        self.width_spin.set_adjustment(width_adj)
        self.width_spin.set_numeric(True)
        self.width_spin.set_property('hexpand', True)
        self.width_spin.set_sensitive(absolute)
        self.height_spin = Gtk.SpinButton()
        self.height_spin.set_adjustment(height_adj)
        self.height_spin.set_numeric(True)
        self.height_spin.set_property('hexpand', True)
        self.height_spin.set_sensitive(absolute)

        flt = conf.filters[i][2]
        self.left_spin.set_value(flt.get('left', 0))
        self.right_spin.set_value(flt.get('right', 0))
        self.top_spin.set_value(flt.get('top', 0))
        self.bottom_spin.set_value(flt.get('bottom', 0))
        self.width_spin.set_value(flt.get('width', 0))
        self.height_spin.set_value(flt.get('height', 0))

        self.grid.attach(left_label, 0, 0, 1, 1)
        self.grid.attach(self.left_spin, 1, 0, 1, 1)
        self.grid.attach(right_label, 0, 1, 1, 1)
        self.grid.attach(self.right_spin, 1, 1, 1, 1)
        self.grid.attach(top_label, 0, 2, 1, 1)
        self.grid.attach(self.top_spin, 1, 2, 1, 1)
        self.grid.attach(bottom_label, 0, 3, 1, 1)
        self.grid.attach(self.bottom_spin, 1, 3, 1, 1)
        self.grid.attach(width_label, 0, 4, 1, 1)
        self.grid.attach(self.width_spin, 1, 4, 1, 1)
        self.grid.attach(height_label, 0, 5, 1, 1)
        self.grid.attach(self.height_spin, 1, 5, 1, 1)

    def _update_crop(self, widget, event, absolute, i):
        flt = conf.filters[i][2]

        l = self.left_spin.get_value_as_int()
        r = self.right_spin.get_value_as_int()
        t = self.top_spin.get_value_as_int()
        b = self.bottom_spin.get_value_as_int()
        w = self.width_spin.get_value_as_int()
        h = self.height_spin.get_value_as_int()

        if absolute:
            flt['width'] = w
            flt['height'] = h

        if not absolute:
            if l:
                flt['left'] = l
        if r:
            flt['right'] = r
        if not absolute:
            if t:
                flt['top'] = t
        if b:
            flt['bottom'] = b

    def _resize(self, i):
        width_adj = Gtk.Adjustment(0, 0, 3840, 1, 10)
        height_adj = Gtk.Adjustment(0, 0, 2160, 1, 10)
        formats = ['GRAY8', 'GRAY16', 'GRAYH', 'GRAYS', 'YUV420P8', 'YUV422P8',
                   'YUV444P8', 'YUV410P8', 'YUV411P8', 'YUV440P8', 'YUV420P9',
                   'YUV422P9', 'YUV444P9', 'YUV420P10', 'YUV422P10',
                   'YUV444P10', 'YUV420P16', 'YUV422P16', 'YUV444P16',
                   'YUV444PH', 'YUV444PS', 'RGB24', 'RGB27', 'RGB30', 'RGB48',
                   'RGBH', 'RGBS', 'COMPATBGR32', 'COMPATYUY2']

        width_label = Gtk.Label('Width')
        width_label.set_halign(Gtk.Align.START)
        height_label = Gtk.Label('Height')
        height_label.set_halign(Gtk.Align.START)
        format_label = Gtk.Label('Format')
        format_label.set_halign(Gtk.Align.START)

        self.width_spin = Gtk.SpinButton()
        self.width_spin.set_adjustment(width_adj)
        self.width_spin.set_numeric(True)
        self.width_spin.set_property('hexpand', True)
        self.height_spin = Gtk.SpinButton()
        self.height_spin.set_adjustment(height_adj)
        self.height_spin.set_numeric(True)
        self.height_spin.set_property('hexpand', True)

        self.format_check = Gtk.CheckButton()

        self.format_cbtext = Gtk.ComboBoxText()
        self.format_cbtext.set_property('hexpand', True)
        for f in formats:
            self.format_cbtext.append_text(f)

        flt = conf.filters[i][2]
        w = flt.get('width', 0)
        if not w:
            w = conf.video['width']
        h = flt.get('height', 0)
        if not h:
            h = conf.video['height']
        self.width_spin.set_value(w)
        self.height_spin.set_value(h)
        f = flt.get('format', '')
        if f:
            self.format_check.set_active(True)
            j = formats.index(f.strip('vs.'))
            self.format_cbtext.set_active(j)
        else:
            self.format_cbtext.set_sensitive(False)

        self.grid.attach(width_label, 0, 0, 2, 1)
        self.grid.attach(self.width_spin, 2, 0, 1, 1)
        self.grid.attach(height_label, 0, 1, 2, 1)
        self.grid.attach(self.height_spin, 2, 1, 1, 1)
        self.grid.attach(format_label, 0, 2, 1, 1)
        self.grid.attach(self.format_check, 1, 2, 1, 1)
        self.grid.attach(self.format_cbtext, 2, 2, 1, 1)

        self.format_check.connect('toggled', self.on_format_toggled)

    def _update_resize(self, widget, event, i):
        flt = conf.filters[i][2]

        w = self.width_spin.get_value_as_int()
        h = self.height_spin.get_value_as_int()
        f = self.format_cbtext.get_active_text()

        flt['width'] = w
        flt['height'] = h

        if self.format_check.get_active():
            flt['format'] = 'vs.' + f
        else:
            if 'format' in flt:
                flt.pop('format')

    def on_format_toggled(self, check):
        s = check.get_active()
        self.format_cbtext.set_sensitive(s)

    def _fsmooth(self, spatial, i):
        tt_adj = Gtk.Adjustment(7, -1, 255, 1, 10)
        st_adj = Gtk.Adjustment(7, -1, 255, 1, 10)

        tt_label = Gtk.Label('Temporal Threshold')
        tt_label.set_halign(Gtk.Align.START)
        st_label = Gtk.Label('Spatial Threshold')
        st_label.set_halign(Gtk.Align.START)
        planes_label = Gtk.Label('Planes')
        planes_label.set_halign(Gtk.Align.START)

        self.tt_spin = Gtk.SpinButton()
        self.tt_spin.set_adjustment(tt_adj)
        self.tt_spin.set_property('hexpand', True)
        self.st_spin = Gtk.SpinButton()
        self.st_spin.set_adjustment(st_adj)
        self.st_spin.set_property('hexpand', True)
        self.st_spin.set_sensitive(spatial)
        self.y_check = Gtk.CheckButton()
        self.y_check.set_label('Y')
        self.y_check.set_active(True)
        self.u_check = Gtk.CheckButton()
        self.u_check.set_label('U')
        self.u_check.set_active(True)
        self.v_check = Gtk.CheckButton()
        self.v_check.set_label('V')
        self.v_check.set_active(True)

        flt = conf.filters[i][2]
        self.tt_spin.set_value(flt.get('temporal_threshold', 7))
        self.st_spin.set_value(flt.get('spatial_threshold', 7))
        p = flt.get('planes', [0, 1, 2])
        if 0 not in p:
            self.y_check.set_active(False)
        if 1 not in p:
            self.u_check.set_active(False)
        if 2 not in p:
            self.v_check.set_active(False)

        self.grid.attach(tt_label, 0, 0, 1, 1)
        self.grid.attach(self.tt_spin, 1, 0, 3, 1)
        self.grid.attach(st_label, 0, 1, 1, 1)
        self.grid.attach(self.st_spin, 1, 1, 3, 1)
        self.grid.attach(planes_label, 0, 2, 1, 1)
        self.grid.attach(self.y_check, 1, 2, 1, 1)
        self.grid.attach(self.u_check, 2, 2, 1, 1)
        self.grid.attach(self.v_check, 3, 2, 1, 1)

    def _update_fsmooth(self, widget, event, spatial, i):
        flt = conf.filters[i][2]

        tt = self.tt_spin.get_value_as_int()
        st = self.st_spin.get_value_as_int()
        y = self.y_check.get_active()
        u = self.u_check.get_active()
        v = self.v_check.get_active()

        if tt != 7:
            flt['temporal_threshold'] = tt
        else:
            if 'temporal_threshold' in flt:
                flt.pop('temporal_threshold')
        if st != 7 and spatial:
            flt['spatial_threshold'] = st
        else:
            if 'spatial_threshold' in flt:
                flt.pop('spatial_threshold')
        if not y or not u or not v:
            flt['planes'] = []
            if y:
                flt['planes'].append(0)
            if u:
                flt['planes'].append(1)
            if v:
                flt['planes'].append(2)
        else:
            if 'planes' in flt:
                flt.pop('planes')

    def _rgvs(self, i):
        mode_adj = Gtk.Adjustment(2, 0, 18, 1, 10)
        modeu_adj = Gtk.Adjustment(2, 0, 18, 1, 10)
        modev_adj = Gtk.Adjustment(2, 0, 18, 1, 10)

        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        modeu_label = Gtk.Label('U Mode')
        modeu_label.set_halign(Gtk.Align.START)
        modev_label = Gtk.Label('V Mode')
        modev_label.set_halign(Gtk.Align.START)

        self.mode_spin = Gtk.SpinButton()
        self.mode_spin.set_adjustment(mode_adj)
        self.mode_spin.set_property('hexpand', True)
        self.modeu_spin = Gtk.SpinButton()
        self.modeu_spin.set_adjustment(modeu_adj)
        self.modeu_spin.set_property('hexpand', True)
        self.modeu_spin.set_sensitive(False)
        self.modev_spin = Gtk.SpinButton()
        self.modev_spin.set_adjustment(modev_adj)
        self.modev_spin.set_property('hexpand', True)
        self.modev_spin.set_sensitive(False)

        self.modeu_check = Gtk.CheckButton()
        self.modev_check = Gtk.CheckButton()

        flt = conf.filters[i][2]
        m = flt.get('mode', [2])
        self.mode_spin.set_value(m[0])
        if len(m) > 1:
            self.modeu_spin.set_value(m[1])
            self.modeu_check.set_active(True)
            self.modeu_spin.set_sensitive(True)
        if len(m) > 2:
            self.modev_spin.set_value(m[2])
            self.modev_check.set_active(True)
            self.modev_spin.set_sensitive(True)

        self.grid.attach(mode_label, 0, 0, 2, 1)
        self.grid.attach(self.mode_spin, 2, 0, 1, 1)
        self.grid.attach(modeu_label, 0, 1, 1, 1)
        self.grid.attach(self.modeu_check, 1, 1, 1, 1)
        self.grid.attach(self.modeu_spin, 2, 1, 1, 1)
        self.grid.attach(modev_label, 0, 2, 1, 1)
        self.grid.attach(self.modev_check, 1, 2, 1, 1)
        self.grid.attach(self.modev_spin, 2, 2, 1, 1)

        self.modeu_check.connect('toggled', self.on_modeu_toggled)
        self.modev_check.connect('toggled', self.on_modev_toggled)

    def _update_rgvs(self, widget, event, i):
        flt = conf.filters[i][2]

        m = self.mode_spin.get_value_as_int()
        su = self.modeu_check.get_active()
        mu = self.modeu_spin.get_value_as_int()
        sv = self.modev_check.get_active()
        mv = self.modev_spin.get_value_as_int()

        flt['mode'] = [m]
        if su:
            flt['mode'].append(mu)
            if sv:
                flt['mode'].append(mv)

    def on_modeu_toggled(self, check):
        s = check.get_active()
        self.modeu_spin.set_sensitive(s)

        if not s:
            self.modev_check.set_active(False)

    def on_modev_toggled(self, check):
        s = check.get_active()
        self.modev_spin.set_sensitive(s)

        if s:
            self.modeu_check.set_active(True)

    def _tsoft(self, i):
        rad_adj = Gtk.Adjustment(4, 1, 7, 1, 1)
        lt_adj = Gtk.Adjustment(4, 0, 255, 1, 10)
        ct_adj = Gtk.Adjustment(4, 0, 255, 1, 10)
        sc_adj = Gtk.Adjustment(0, 0, 254, 1, 10)

        rad_label = Gtk.Label('Radius')
        rad_label.set_halign(Gtk.Align.START)
        lt_label = Gtk.Label('Luma Threshold')
        lt_label.set_halign(Gtk.Align.START)
        ct_label = Gtk.Label('Chroma Threshold')
        ct_label.set_halign(Gtk.Align.START)
        sc_label = Gtk.Label('Scene Change')
        sc_label.set_halign(Gtk.Align.START)

        self.rad_spin = Gtk.SpinButton()
        self.rad_spin.set_adjustment(rad_adj)
        self.rad_spin.set_property('hexpand', True)
        self.lt_spin = Gtk.SpinButton()
        self.lt_spin.set_adjustment(lt_adj)
        self.lt_spin.set_property('hexpand', True)
        self.ct_spin = Gtk.SpinButton()
        self.ct_spin.set_adjustment(ct_adj)
        self.ct_spin.set_property('hexpand', True)
        self.sc_spin = Gtk.SpinButton()
        self.sc_spin.set_adjustment(sc_adj)
        self.sc_spin.set_property('hexpand', True)

        flt = conf.filters[i][2]
        self.rad_spin.set_value(flt.get('radius', 4))
        self.lt_spin.set_value(flt.get('luma_threshold', 4))
        self.ct_spin.set_value(flt.get('chroma_threshold', 4))
        self.sc_spin.set_value(flt.get('scenechange', 0))

        self.grid.attach(rad_label, 0, 0, 1, 1)
        self.grid.attach(self.rad_spin, 1, 0, 1, 1)
        self.grid.attach(lt_label, 0, 1, 1, 1)
        self.grid.attach(self.lt_spin, 1, 1, 1, 1)
        self.grid.attach(ct_label, 0, 2, 1, 1)
        self.grid.attach(self.ct_spin, 1, 2, 1, 1)
        self.grid.attach(sc_label, 0, 3, 1, 1)
        self.grid.attach(self.sc_spin, 1, 3, 1, 1)

    def _update_tsoft(self, widget, event, i):
        flt = conf.filters[i][2]

        rad = self.rad_spin.get_value_as_int()
        lt = self.lt_spin.get_value_as_int()
        ct = self.ct_spin.get_value_as_int()
        sc = self.sc_spin.get_value_as_int()

        if rad != 4:
            flt['radius'] = rad
        else:
            if 'radius' in flt:
                flt.pop('radius')
        if lt != 4:
            flt['luma_threshold'] = lt
        else:
            if 'luma_threshold' in flt:
                flt.pop('luma_threshold')
        if ct != 4:
            flt['chroma_threshold'] = ct
        else:
            if 'chroma_threshold' in flt:
                flt.pop('chroma_threshold')
        if sc != 0:
            flt['scenechange'] = sc
        else:
            if 'scenechange' in flt:
                flt.pop('scenechange')

    def _f3kdb(self, i):
        y_adj = Gtk.Adjustment(64, 0, 80, 1, 10)
        cb_adj = Gtk.Adjustment(64, 0, 80, 1, 10)
        cr_adj = Gtk.Adjustment(64, 0, 80, 1, 10)
        grainy_adj = Gtk.Adjustment(64, 0, 80, 1, 10)
        grainc_adj = Gtk.Adjustment(64, 0, 80, 1, 10)
        depth_adj = Gtk.Adjustment(16, 8, 16, 1, 1)
        modes = ['2 pixels', '4 pixels']
        dithers = ['None', 'Ordered', 'Floyd-Steinberg']

        y_label = Gtk.Label('Y')
        y_label.set_halign(Gtk.Align.START)
        cb_label = Gtk.Label('Cb')
        cb_label.set_halign(Gtk.Align.START)
        cr_label = Gtk.Label('Cr')
        cr_label.set_halign(Gtk.Align.START)
        grainy_label = Gtk.Label('Grain Y')
        grainy_label.set_halign(Gtk.Align.START)
        grainc_label = Gtk.Label('Grain C')
        grainc_label.set_halign(Gtk.Align.START)
        depth_label = Gtk.Label('Output Depth')
        depth_label.set_halign(Gtk.Align.START)
        dither_label = Gtk.Label('Dithering')
        dither_label.set_halign(Gtk.Align.START)
        mode_label = Gtk.Label('Sample Mode')
        mode_label.set_halign(Gtk.Align.START)
        blur_label = Gtk.Label('Blur First')
        blur_label.set_halign(Gtk.Align.START)
        dyngrain_label = Gtk.Label('Dynamic Grain')
        dyngrain_label.set_halign(Gtk.Align.START)

        self.y_spin = Gtk.SpinButton()
        self.y_spin.set_adjustment(y_adj)
        self.y_spin.set_property('hexpand', True)
        self.cb_spin = Gtk.SpinButton()
        self.cb_spin.set_adjustment(cb_adj)
        self.cb_spin.set_property('hexpand', True)
        self.cr_spin = Gtk.SpinButton()
        self.cr_spin.set_adjustment(cr_adj)
        self.cr_spin.set_property('hexpand', True)
        self.grainy_spin = Gtk.SpinButton()
        self.grainy_spin.set_adjustment(grainy_adj)
        self.grainy_spin.set_property('hexpand', True)
        self.grainc_spin = Gtk.SpinButton()
        self.grainc_spin.set_adjustment(grainc_adj)
        self.grainc_spin.set_property('hexpand', True)
        self.depth_spin = Gtk.SpinButton()
        self.depth_spin.set_adjustment(depth_adj)
        self.depth_spin.set_property('hexpand', True)

        self.dither_cbtext = Gtk.ComboBoxText()
        self.dither_cbtext.set_property('hexpand', True)
        for a in dithers:
            self.dither_cbtext.append_text(a)
        self.dither_cbtext.set_active(2)
        self.mode_cbtext = Gtk.ComboBoxText()
        self.mode_cbtext.set_property('hexpand', True)
        for m in modes:
            self.mode_cbtext.append_text(m)
        self.mode_cbtext.set_active(1)

        self.dyngrain_check = Gtk.CheckButton()
        self.dyngrain_check.set_active(False)
        self.blur_check = Gtk.CheckButton()
        self.blur_check.set_active(False)

        flt = conf.filters[i][2]
        self.y_spin.set_value(flt.get('y', 64))
        self.cb_spin.set_value(flt.get('cb', 64))
        self.cr_spin.set_value(flt.get('cr', 64))
        self.grainy_spin.set_value(flt.get('grainy', 64))
        self.grainc_spin.set_value(flt.get('grainc', 64))
        self.depth_spin.set_value(flt.get('output_depth', 8))
        self.dither_cbtext.set_active(flt.get('dither_algo', 3) - 1)
        self.mode_cbtext.set_active(flt.get('dither_algo', 2) - 1)
        self.blur_check.set_active(flt.get('blur_first', True))
        self.dyngrain_check.set_active(flt.get('dynamic_grain', False))

        self.grid.attach(y_label, 0, 0, 1, 1)
        self.grid.attach(self.y_spin, 1, 0, 1, 1)
        self.grid.attach(cb_label, 0, 1, 1, 1)
        self.grid.attach(self.cb_spin, 1, 1, 1, 1)
        self.grid.attach(cr_label, 0, 2, 1, 1)
        self.grid.attach(self.cr_spin, 1, 2, 1, 1)
        self.grid.attach(grainy_label, 0, 3, 1, 1)
        self.grid.attach(self.grainy_spin, 1, 3, 1, 1)
        self.grid.attach(grainc_label, 0, 4, 1, 1)
        self.grid.attach(self.grainc_spin, 1, 4, 1, 1)
        self.grid.attach(depth_label, 0, 5, 1, 1)
        self.grid.attach(self.depth_spin, 1, 5, 1, 1)
        self.grid.attach(dither_label, 0, 6, 1, 1)
        self.grid.attach(self.dither_cbtext, 1, 6, 1, 1)
        self.grid.attach(mode_label, 0, 7, 1, 1)
        self.grid.attach(self.mode_cbtext, 1, 7, 1, 1)
        self.grid.attach(blur_label, 0, 8, 1, 1)
        self.grid.attach(self.blur_check, 1, 8, 1, 1)
        self.grid.attach(dyngrain_label, 0, 9, 1, 1)
        self.grid.attach(self.dyngrain_check, 1, 9, 1, 1)

        self.depth_spin.connect('changed', self.on_depth_changed)

    def _update_f3kdb(self, widget, event, i):
        flt = conf.filters[i][2]

        y = self.y_spin.get_value_as_int()
        cb = self.cb_spin.get_value_as_int()
        cr = self.cr_spin.get_value_as_int()
        gy = self.grainy_spin.get_value_as_int()
        gc = self.grainc_spin.get_value_as_int()
        od = self.depth_spin.get_value_as_int()
        da = self.dither_cbtext.get_active() + 1
        sm = self.mode_cbtext.get_active() + 1
        bf = self.blur_check.get_active()
        dg = self.dyngrain_check.get_active()

        if y != 64:
            flt['y'] = y
        else:
            if 'y' in flt:
                flt.pop('y')
        if cb != 64:
            flt['cb'] = cb
        else:
            if 'cb' in flt:
                flt.pop('cb')
        if cr != 64:
            flt['cr'] = cr
        else:
            if 'cr' in flt:
                flt.pop('cr')
        if gy != 64:
            flt['grainy'] = gy
        else:
            if 'grainy' in flt:
                flt.pop('grainy')
        if gc != 64:
            flt['grainc'] = gc
        else:
            if 'grainc' in flt:
                flt.pop('grainc')
        if od != 8:
            flt['output_depth'] = od
        else:
            if 'output_depth' in flt:
                flt.pop('output_depth')
        if da != 3 and od != 16:
            flt['dither_algo'] = da
        else:
            if 'dither_algo' in flt:
                flt.pop('dither_algo')
        if sm != 2:
            flt['sample_mode'] = sm
        else:
            if 'sample_mode' in flt:
                flt.pop('sample_mode')
        if not bf:
            flt['blur_first'] = bf
        else:
            if 'blur_first' in flt:
                flt.pop('blur_first')
        if dg:
            flt['dynamic_grain'] = dg
        else:
            if 'dynamic_grain' in flt:
                flt.pop('dynamic_grain')

    def on_depth_changed(self, spin):
        if spin.get_value_as_int() == 16:
            self.dither_cbtext.set_sensitive(False)
        else:
            self.dither_cbtext.set_sensitive(True)

    def _trim(self, i):
        first_adj = Gtk.Adjustment(0, 0, 1000000, 1, 100)
        last_adj = Gtk.Adjustment(0, 0, 1000000, 1, 100)

        first_label = Gtk.Label('First')
        first_label.set_halign(Gtk.Align.START)
        last_label = Gtk.Label('Last')
        last_label.set_halign(Gtk.Align.START)

        self.first_spin = Gtk.SpinButton()
        self.first_spin.set_adjustment(first_adj)
        self.first_spin.set_numeric(True)
        self.first_spin.set_property('hexpand', True)
        self.last_spin = Gtk.SpinButton()
        self.last_spin.set_adjustment(last_adj)
        self.last_spin.set_numeric(True)
        self.last_spin.set_property('hexpand', True)

        flt = conf.filters[i][2]
        self.first_spin.set_value(flt.get('first', 0))
        self.last_spin.set_value(flt.get('last', 0))

        self.grid.attach(first_label, 0, 0, 1, 1)
        self.grid.attach(self.first_spin, 1, 0, 1, 1)
        self.grid.attach(last_label, 0, 1, 1, 1)
        self.grid.attach(self.last_spin, 1, 1, 1, 1)

    def _update_trim(self, widget, event, i):
        flt = conf.filters[i][2]

        f = self.first_spin.get_value_as_int()
        l = self.last_spin.get_value_as_int()

        flt['first'] = f
        flt['last'] = l
        conf.trim = [f, l]

# vim: ts=4 sw=4 et:
