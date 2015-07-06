#!/usr/bin/env python3

import os
import re
import subprocess
import yaml
from concurrent.futures import ThreadPoolExecutor
from gi.repository import Gio, GLib, GObject, Gtk
from pyanimenc.helpers import Chapters, Encode, MatroskaOps
from threading import Lock

VERSION = '0.1b1'
AUTHOR = 'Maxime Gauduin <alucryd@gmail.com>'

VENCS = ['x264', 'x265']
VTYPES = {'V_MPEG4/ISO/AVC': 'h264', 'V_MPEGH/ISO/HEVC': 'h265',
          'V_MS/VFW/FOURCC': 'xvid'}
AENCS = ['fdkaac', 'lame']
ATYPES = {'A_AAC': 'aac', 'A_AAC/MPEG2/LC/SBR': 'aac', 'A_AC3': 'ac3',
          'A_DTS': 'dts', 'A_FLAC': 'flac', 'A_MP3': 'mp3', 'A_TRUEHD': 'thd',
          'A_VORBIS': 'ogg', 'A_WAVPACK4': 'wv'}
STYPES = {'S_HDMV/PGS': 'sup', 'S_TEXT/ASS': 'ass', 'S_TEXT/SSA': 'ass',
          'S_TEXT/UTF8': 'srt', 'S_VOBSUB': 'sub'}

# Filters
sflt = Gtk.FileFilter()
sflt.set_name('VapourSynth scripts')
sflt.add_pattern('*.vpy')

vflt = Gtk.FileFilter()
vflt.set_name('Video files')
for p in ('*.avi', '*.flv', '*.mkv', '*.mp4', '*.ogm'):
    vflt.add_pattern(p)

aflt = Gtk.FileFilter()
aflt.set_name('Audio files')
for p in ('*.aac', '*.ac3', '*.dts', '*.flac', '*.mka', '*.mp3', '*.mp4',
          '*.mpc', '*.ogg', '*.thd', '*.wav', '*.wv'):
    aflt.add_pattern(p)

class Config:

    def __init__(self):
        # Initialize all codecs and filters configuration
        if self._find_enc('fdkaac'):
            self.fdkaac()
        else:
            AENCS.remove('fdkaac')
        if self._find_enc('lame'):
            self.lame()
        else:
            AENCS.remove('lame')
        self._find_x264()
        self._find_x265()
        self.vs()
        self.rgvs()
        self.tsoft()
        self.fsmooth()
        self.f3kdb()

    def _find_enc(self, x):
        if os.path.isfile('/usr/bin/' + x):
            return True
        else:
            return False

    def _find_x264(self):
        self.x264_depths = []
        if self._find_enc('x264'):
            self.x264_depths.append('8')
        if self._find_enc('x264-10bit'):
            self.x264_depths.append('10')
        if self.x264_depths:
            #self.x264_depths.sort()
            self.x264()
        else:
            VENCS.remove('x264')

    def _find_x265(self):
        self.x265_depths = []
        if self._find_enc('x265'):
            for d in ['8', '10', '12']:
                cmd = ['x265', '--output-depth', d, '--version']
                cmd = ' '.join(cmd)
                self.proc = subprocess.Popen(cmd,
                                             shell=True,
                                             stderr=subprocess.PIPE,
                                             universal_newlines=True)
                line = self.proc.stderr.readline()
                while line:
                    depth = re.findall('(8|10|12)bit', line)
                    if depth:
                        depth = depth[0].strip('bit')
                        if not depth in self.x265_depths:
                            self.x265_depths.append(depth)
                    line = self.proc.stderr.readline()
        if self.x265_depths:
            self.x265()
        else:
            VENCS.remove('x265')

    def fdkaac(self):
        fdkaac_modes = ['CBR', 'VBR']
        fdkaac_bitrate = Gtk.Adjustment(192, 0, 320, 1, 10)
        fdkaac_quality = Gtk.Adjustment(4, 1, 5, 1)
        fdkaac_conts = ['aac', 'm4a']

        self.fdkaac_bitrate_spin = Gtk.SpinButton()
        self.fdkaac_bitrate_spin.set_property('hexpand', True)
        self.fdkaac_bitrate_spin.set_numeric(True)
        self.fdkaac_bitrate_spin.set_adjustment(fdkaac_bitrate)

        self.fdkaac_quality_spin = Gtk.SpinButton()
        self.fdkaac_quality_spin.set_property('hexpand', True)
        self.fdkaac_quality_spin.set_numeric(True)
        self.fdkaac_quality_spin.set_adjustment(fdkaac_quality)

        self.fdkaac_mode_cbtext = Gtk.ComboBoxText()
        self.fdkaac_mode_cbtext.set_property('hexpand', True)
        for m in fdkaac_modes:
            self.fdkaac_mode_cbtext.append_text(m)
        self.fdkaac_mode_cbtext.set_active(0)

        self.fdkaac_cont_cbtext = Gtk.ComboBoxText()
        self.fdkaac_cont_cbtext.set_property('hexpand', True)
        for c in fdkaac_conts:
            self.fdkaac_cont_cbtext.append_text(c)
        self.fdkaac_cont_cbtext.set_active(0)

    def lame(self):
        lame_modes = ['CBR', 'ABR', 'VBR']
        lame_bitrate = Gtk.Adjustment(320, 0, 320, 1, 10)
        lame_quality = Gtk.Adjustment(4, 0, 9, 1)

        self.lame_bitrate_spin = Gtk.SpinButton()
        self.lame_bitrate_spin.set_property('hexpand', True)
        self.lame_bitrate_spin.set_numeric(True)
        self.lame_bitrate_spin.set_adjustment(lame_bitrate)

        self.lame_quality_spin = Gtk.SpinButton()
        self.lame_quality_spin.set_property('hexpand', True)
        self.lame_quality_spin.set_numeric(True)
        self.lame_quality_spin.set_adjustment(lame_quality)

        self.lame_mode_cbtext = Gtk.ComboBoxText()
        self.lame_mode_cbtext.set_property('hexpand', True)
        for m in lame_modes:
            self.lame_mode_cbtext.append_text(m)
        self.lame_mode_cbtext.set_active(0)

    def x264(self):
        x264_depths = ['8']
        x264_quality = Gtk.Adjustment(18, 1, 51, 1, 10)
        x264_presets = ['none', 'ultrafast', 'superfast', 'veryfast', 'faster',
                        'fast', 'medium', 'slow', 'slower', 'veryslow',
                        'placebo']
        x264_tunes = ['none', 'film', 'animation', 'grain', 'stillimage',
                      'psnr', 'ssim', 'fastdecode', 'zerolatency']
        x264_conts = ['264', 'flv', 'mkv']

        self.x264_depth_cbtext = Gtk.ComboBoxText()
        self.x264_depth_cbtext.set_property('hexpand', True)
        for d in self.x264_depths:
            self.x264_depth_cbtext.append_text(d)
        self.x264_depth_cbtext.set_active(0)

        self.x264_quality_spin = Gtk.SpinButton()
        self.x264_quality_spin.set_property('hexpand', True)
        self.x264_quality_spin.set_numeric(True)
        self.x264_quality_spin.set_adjustment(x264_quality)

        self.x264_preset_cbtext = Gtk.ComboBoxText()
        self.x264_preset_cbtext.set_property('hexpand', True)
        for p in x264_presets:
            self.x264_preset_cbtext.append_text(p)
        self.x264_preset_cbtext.set_active(6)

        self.x264_tune_cbtext = Gtk.ComboBoxText()
        self.x264_tune_cbtext.set_property('hexpand', True)
        for t in x264_tunes:
            self.x264_tune_cbtext.append_text(t)
        self.x264_tune_cbtext.set_active(0)

        self.x264_cont_cbtext = Gtk.ComboBoxText()
        self.x264_cont_cbtext.set_property('hexpand', True)
        for c in x264_conts:
            self.x264_cont_cbtext.append_text(c)
        self.x264_cont_cbtext.set_active(0)

    def x265(self):
        x265_quality = Gtk.Adjustment(18, 1, 51, 1, 10)
        x265_presets = ['none', 'ultrafast', 'superfast', 'veryfast', 'faster',
                        'fast', 'medium', 'slow', 'slower', 'veryslow',
                        'placebo']
        x265_tunes = ['none', 'psnr', 'ssim', 'fastdecode', 'zerolatency']
        x265_conts = ['265']

        self.x265_depth_cbtext = Gtk.ComboBoxText()
        self.x265_depth_cbtext.set_property('hexpand', True)
        for d in self.x265_depths:
            self.x265_depth_cbtext.append_text(d)
        self.x265_depth_cbtext.set_active(0)

        self.x265_quality_spin = Gtk.SpinButton()
        self.x265_quality_spin.set_property('hexpand', True)
        self.x265_quality_spin.set_numeric(True)
        self.x265_quality_spin.set_adjustment(x265_quality)

        self.x265_preset_cbtext = Gtk.ComboBoxText()
        self.x265_preset_cbtext.set_property('hexpand', True)
        for p in x265_presets:
            self.x265_preset_cbtext.append_text(p)
        self.x265_preset_cbtext.set_active(6)

        self.x265_tune_cbtext = Gtk.ComboBoxText()
        self.x265_tune_cbtext.set_property('hexpand', True)
        for t in x265_tunes:
            self.x265_tune_cbtext.append_text(t)
        self.x265_tune_cbtext.set_active(0)

        self.x265_cont_cbtext = Gtk.ComboBoxText()
        self.x265_cont_cbtext.set_property('hexpand', True)
        for c in x265_conts:
            self.x265_cont_cbtext.append_text(c)
        self.x265_cont_cbtext.set_active(0)

    def vs(self):
        fpsnums = Gtk.Adjustment(24000, 0, 256000, 1, 100)
        fpsdens = Gtk.Adjustment(1001, 0, 256000, 1, 100)
        tcrops = Gtk.Adjustment(0, 0, 2160, 1, 10)
        bcrops = Gtk.Adjustment(0, 0, 2160, 1, 10)
        lcrops = Gtk.Adjustment(0, 0, 3840, 1, 10)
        rcrops = Gtk.Adjustment(0, 0, 3840, 1, 10)
        hsizes = Gtk.Adjustment(0, 0, 2160, 1, 10)
        wsizes = Gtk.Adjustment(0, 0, 3840, 1, 10)
        resize_flts = ['bilinear', 'bicubic', 'point', 'gauss', 'sinc',
                       'lanczos', 'spline']
        sdenoise_flts = ['RemoveGrain']
        tdenoise_flts = ['FluxSmoothT', 'TemporalSoften']
        stdenoise_flts = ['FluxSmoothST']
        deband_flts = ['f3kdb']

        #--Basic--#
        self.fps_check = Gtk.CheckButton()
        self.fps_check.set_label('FPS')
        self.crop_check = Gtk.CheckButton()
        self.crop_check.set_label('Crop')
        self.resize_check = Gtk.CheckButton()
        self.resize_check.set_label('Resize')

        self.fpsnum_spin = Gtk.SpinButton()
        self.fpsnum_spin.set_adjustment(fpsnums)
        self.fpsnum_spin.set_numeric(True)
        self.fpsnum_spin.set_property('hexpand', True)
        self.fpsden_spin = Gtk.SpinButton()
        self.fpsden_spin.set_adjustment(fpsdens)
        self.fpsden_spin.set_numeric(True)
        self.fpsden_spin.set_property('hexpand', True)

        self.tcrop_spin = Gtk.SpinButton()
        self.tcrop_spin.set_adjustment(tcrops)
        self.tcrop_spin.set_numeric(True)
        self.tcrop_spin.set_property('hexpand', True)
        self.bcrop_spin = Gtk.SpinButton()
        self.bcrop_spin.set_adjustment(bcrops)
        self.bcrop_spin.set_numeric(True)
        self.bcrop_spin.set_property('hexpand', True)
        self.lcrop_spin = Gtk.SpinButton()
        self.lcrop_spin.set_adjustment(lcrops)
        self.lcrop_spin.set_numeric(True)
        self.lcrop_spin.set_property('hexpand', True)
        self.rcrop_spin = Gtk.SpinButton()
        self.rcrop_spin.set_adjustment(rcrops)
        self.rcrop_spin.set_numeric(True)
        self.rcrop_spin.set_property('hexpand', True)

        self.wresize_spin = Gtk.SpinButton()
        self.wresize_spin.set_adjustment(wsizes)
        self.wresize_spin.set_numeric(True)
        self.wresize_spin.set_property('hexpand', True)
        self.hresize_spin = Gtk.SpinButton()
        self.hresize_spin.set_adjustment(hsizes)
        self.hresize_spin.set_numeric(True)
        self.hresize_spin.set_property('hexpand', True)
        self.resize_cbtext = Gtk.ComboBoxText()
        for f in resize_flts:
            self.resize_cbtext.append_text(f)
        self.resize_cbtext.set_active(1)
        self.resize_cbtext.set_property('hexpand', True)

        #--Filters--#
        self.sdenoise_check = Gtk.CheckButton()
        self.sdenoise_check.set_label('Spatial')
        self.sdenoise_cbtext = Gtk.ComboBoxText()
        for f in sdenoise_flts:
            self.sdenoise_cbtext.append_text(f)
        self.sdenoise_cbtext.set_active(0)

        self.tdenoise_check = Gtk.CheckButton()
        self.tdenoise_check.set_label('Temporal')
        self.tdenoise_cbtext = Gtk.ComboBoxText()
        for f in tdenoise_flts:
            self.tdenoise_cbtext.append_text(f)
        self.tdenoise_cbtext.set_active(0)

        self.stdenoise_check = Gtk.CheckButton()
        self.stdenoise_check.set_label('Spatio-Temporal')
        self.stdenoise_cbtext = Gtk.ComboBoxText()
        for f in stdenoise_flts:
            self.stdenoise_cbtext.append_text(f)
        self.stdenoise_cbtext.set_active(0)

        self.deband_check = Gtk.CheckButton()
        self.deband_check.set_label('Deband')
        self.deband_cbtext = Gtk.ComboBoxText()
        for f in deband_flts:
            self.deband_cbtext.append_text(f)
        self.deband_cbtext.set_active(0)

    def rgvs(self):
        rgvs_mode = Gtk.Adjustment(2, 0, 18, 1, 10)
        rgvs_modeu = Gtk.Adjustment(2, 0, 18, 1, 10)
        rgvs_modev = Gtk.Adjustment(2, 0, 18, 1, 10)

        self.rgvs_adv_check = Gtk.CheckButton()
        self.rgvs_mode_spin = Gtk.SpinButton()
        self.rgvs_mode_spin.set_adjustment(rgvs_mode)
        self.rgvs_mode_spin.set_property('hexpand', True)
        self.rgvs_modeu_spin = Gtk.SpinButton()
        self.rgvs_modeu_spin.set_adjustment(rgvs_modeu)
        self.rgvs_modeu_spin.set_property('hexpand', True)
        self.rgvs_modev_spin = Gtk.SpinButton()
        self.rgvs_modev_spin.set_adjustment(rgvs_modev)
        self.rgvs_modev_spin.set_property('hexpand', True)

    def tsoft(self):
        tsoft_rad = Gtk.Adjustment(4, 1, 7, 1, 1)
        tsoft_lt = Gtk.Adjustment(2, 0, 255, 1, 10)
        tsoft_ct = Gtk.Adjustment(4, 0, 255, 1, 10)
        tsoft_sc = Gtk.Adjustment(12, 0, 254, 1, 10)

        self.tsoft_rad_spin = Gtk.SpinButton()
        self.tsoft_rad_spin.set_adjustment(tsoft_rad)
        self.tsoft_rad_spin.set_property('hexpand', True)
        self.tsoft_lt_spin = Gtk.SpinButton()
        self.tsoft_lt_spin.set_adjustment(tsoft_lt)
        self.tsoft_lt_spin.set_property('hexpand', True)
        self.tsoft_ct_spin = Gtk.SpinButton()
        self.tsoft_ct_spin.set_adjustment(tsoft_ct)
        self.tsoft_ct_spin.set_property('hexpand', True)
        self.tsoft_sc_spin = Gtk.SpinButton()
        self.tsoft_sc_spin.set_adjustment(tsoft_sc)
        self.tsoft_sc_spin.set_property('hexpand', True)

    def fsmooth(self):
        fsmooth_st = Gtk.Adjustment(7, -1, 255, 1, 10)
        fsmooth_tt = Gtk.Adjustment(7, -1, 255, 1, 10)

        self.fsmooth_st_spin = Gtk.SpinButton()
        self.fsmooth_st_spin.set_adjustment(fsmooth_st)
        self.fsmooth_st_spin.set_property('hexpand', True)
        self.fsmooth_tt_spin = Gtk.SpinButton()
        self.fsmooth_tt_spin.set_adjustment(fsmooth_tt)
        self.fsmooth_tt_spin.set_property('hexpand', True)
        self.fsmooth_y_check = Gtk.CheckButton()
        self.fsmooth_y_check.set_label('Y')
        self.fsmooth_y_check.set_active(True)
        self.fsmooth_u_check = Gtk.CheckButton()
        self.fsmooth_u_check.set_label('U')
        self.fsmooth_u_check.set_active(True)
        self.fsmooth_v_check = Gtk.CheckButton()
        self.fsmooth_v_check.set_label('V')
        self.fsmooth_v_check.set_active(True)

    def f3kdb(self):
        f3kdb_presets = ['depth', 'low', 'medium', 'high', 'veryhigh']
        f3kdb_planes = ['all', 'luma', 'chroma']
        f3kdb_depths = Gtk.Adjustment(16, 8, 16, 1, 1)

        self.f3kdb_preset_cbtext = Gtk.ComboBoxText()
        self.f3kdb_preset_cbtext.set_property('hexpand', True)
        for p in f3kdb_presets:
            self.f3kdb_preset_cbtext.append_text(p)
        self.f3kdb_preset_cbtext.set_active(2)
        self.f3kdb_plane_cbtext = Gtk.ComboBoxText()
        self.f3kdb_plane_cbtext.set_property('hexpand', True)
        for p in f3kdb_planes:
            self.f3kdb_plane_cbtext.append_text(p)
        self.f3kdb_plane_cbtext.set_active(0)
        self.f3kdb_grain_check = Gtk.CheckButton()
        self.f3kdb_grain_check.set_active(True)
        self.f3kdb_depth_spin = Gtk.SpinButton()
        self.f3kdb_depth_spin.set_adjustment(f3kdb_depths)
        self.f3kdb_depth_spin.set_property('hexpand', True)

class MainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title='pyanimenc')
        self.set_default_size(800, 600)

        #--Header Bar--#
        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.set_property('title', 'pyanimenc')

        tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        tools_box.set_property('margin', 6)
        tools_sccr_button = Gtk.Button()
        tools_sccr_button.set_label('Script Creator')
        tools_sccr_button.connect('clicked', self.on_sccr_clicked)
        tools_ched_button = Gtk.Button()
        tools_ched_button.set_label('Chapter Editor')
        tools_ched_button.connect('clicked', self.on_ched_clicked)
        tools_box.pack_start(tools_sccr_button, True, True, 0)
        tools_box.pack_start(tools_ched_button, True, True, 0)
        tools_box.show_all()

        tools_popover = Gtk.Popover()
        tools_popover.add(tools_box)

        tools_mbutton = Gtk.MenuButton()
        tools_mbutton.set_label('Tools')
        tools_mbutton.set_direction(Gtk.ArrowType.DOWN)
        tools_mbutton.set_use_popover(True)
        tools_mbutton.set_popover(tools_popover)

        about_button = Gtk.Button()
        about_button.set_label('About')
        about_button.connect('clicked', self.on_about_clicked)

        hbar.pack_start(tools_mbutton)
        hbar.pack_end(about_button)

        self.set_titlebar(hbar)

        #--Notebook--#
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        input_box.set_property('margin', 6)
        queue_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        queue_box.set_property('margin', 6)

        notebook = Gtk.Notebook()
        input_label = Gtk.Label('Input')
        notebook.append_page(input_box, input_label)
        queue_label = Gtk.Label('Queue')
        notebook.append_page(queue_box, queue_label)

        for tab in notebook.get_children():
            notebook.child_set_property(tab, 'tab-expand', True)

        main_box.pack_start(notebook, True, True, 0)

        #---Input---#
        input_grid = Gtk.Grid()
        input_grid.set_column_spacing(6)
        input_grid.set_row_spacing(6)

        conf_icon = Gio.ThemedIcon(name='applications-system-symbolic')
        queue_icon = Gio.ThemedIcon(name='list-add-symbolic')

        manual_label = Gtk.Label()
        manual_label.set_markup('<b>Manual</b>')
        manual_label.set_halign(Gtk.Align.CENTER)
        vid_label = Gtk.Label('Video')
        vid_label.set_angle(90)
        aud_label = Gtk.Label('Audio')
        aud_label.set_angle(90)

        self.vsrc_fcbutton = Gtk.FileChooserButton()
        self.vsrc_fcbutton.set_property('hexpand', True)
        self.vsrc_fcbutton.add_filter(sflt)
        self.vsrc_fcbutton.connect('file-set', self.on_vsrc_file_set)
        self.asrc_fcbutton = Gtk.FileChooserButton()
        self.asrc_fcbutton.set_property('hexpand', True)
        self.asrc_fcbutton.add_filter(aflt)
        self.asrc_fcbutton.connect('file-set', self.on_asrc_file_set)

        self.venc_cbtext = Gtk.ComboBoxText()
        self.venc_cbtext.set_property('hexpand', True)
        self.aenc_cbtext = Gtk.ComboBoxText()
        self.aenc_cbtext.set_property('hexpand', True)

        vqueue_image = Gtk.Image.new_from_gicon(queue_icon,
                                                Gtk.IconSize.BUTTON)
        self.vqueue_button = Gtk.Button()
        self.vqueue_button.set_image(vqueue_image)
        self.vqueue_button.set_sensitive(False)
        self.vqueue_button.connect('clicked', self.on_vqueue_clicked)
        vconf_image = Gtk.Image.new_from_gicon(conf_icon, Gtk.IconSize.BUTTON)
        self.vconf_button = Gtk.Button()
        self.vconf_button.set_image(vconf_image)
        self.vconf_button.connect('clicked', self.on_conf_clicked, 'manual',
                                  'video')
        aqueue_image = Gtk.Image.new_from_gicon(queue_icon,
                                                Gtk.IconSize.BUTTON)
        self.aqueue_button = Gtk.Button()
        self.aqueue_button.set_image(aqueue_image)
        self.aqueue_button.set_sensitive(False)
        self.aqueue_button.connect('clicked', self.on_aqueue_clicked)
        aconf_image = Gtk.Image.new_from_gicon(conf_icon, Gtk.IconSize.BUTTON)
        self.aconf_button = Gtk.Button()
        self.aconf_button.set_image(aconf_image)
        self.aconf_button.connect('clicked', self.on_conf_clicked, 'manual',
                                  'audio')

        vsep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        hsep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

        auto_label = Gtk.Label()
        auto_label.set_markup('<b>One-Click</b>')
        auto_label.set_halign(Gtk.Align.CENTER)

        self.auto_src_fcbutton = Gtk.FileChooserButton()
        self.auto_src_fcbutton.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        self.auto_src_fcbutton.set_property('hexpand', True)
        self.auto_src_fcbutton.connect('file-set', self.on_auto_src_file_set)

        self.auto_venc_cbtext = Gtk.ComboBoxText()
        self.auto_venc_cbtext.set_property('hexpand', True)
        self.auto_aenc_cbtext = Gtk.ComboBoxText()
        self.auto_aenc_cbtext.set_property('hexpand', True)

        auto_sconf_image = Gtk.Image.new_from_gicon(conf_icon,
                                                    Gtk.IconSize.BUTTON)
        auto_sconf_button = Gtk.Button()
        auto_sconf_button.set_image(auto_sconf_image)
        auto_sconf_button.connect('clicked', self.on_auto_sconf_clicked)
        auto_vconf_image = Gtk.Image.new_from_gicon(conf_icon,
                                                    Gtk.IconSize.BUTTON)
        auto_vconf_button = Gtk.Button()
        auto_vconf_button.set_image(auto_vconf_image)
        auto_vconf_button.connect('clicked', self.on_conf_clicked, 'auto',
                                  'video')
        auto_aconf_image = Gtk.Image.new_from_gicon(conf_icon,
                                                    Gtk.IconSize.BUTTON)
        auto_aconf_button = Gtk.Button()
        auto_aconf_button.set_image(auto_aconf_image)
        auto_aconf_button.connect('clicked', self.on_conf_clicked, 'auto',
                                  'audio')

        auto_queue_image = Gtk.Image.new_from_gicon(queue_icon,
                                                    Gtk.IconSize.BUTTON)
        self.auto_queue_button = Gtk.Button()
        self.auto_queue_button.set_image(auto_queue_image)
        self.auto_queue_button.set_sensitive(False)
        self.auto_queue_button.connect('clicked', self.on_auto_queue_clicked)

        input_grid.attach(manual_label, 0, 0, 3, 1)
        input_grid.attach(vid_label, 0, 1, 1, 2)
        input_grid.attach(self.vsrc_fcbutton, 1, 1, 1, 1)
        input_grid.attach_next_to(self.vqueue_button, self.vsrc_fcbutton,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(self.venc_cbtext, 1, 2, 1, 1)
        input_grid.attach_next_to(self.vconf_button, self.venc_cbtext,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(aud_label, 0, 3, 1, 2)
        input_grid.attach(self.asrc_fcbutton, 1, 3, 1, 1)
        input_grid.attach_next_to(self.aqueue_button, self.asrc_fcbutton,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(self.aenc_cbtext, 1, 4, 1, 1)
        input_grid.attach_next_to(self.aconf_button, self.aenc_cbtext,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(vsep, 3, 0, 1, 5)
        input_grid.attach(auto_label, 4, 0, 2 ,1)
        input_grid.attach(self.auto_src_fcbutton, 4, 1, 1, 1)
        input_grid.attach_next_to(auto_sconf_button, self.auto_src_fcbutton,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(self.auto_venc_cbtext, 4, 2, 1, 1)
        input_grid.attach_next_to(auto_vconf_button, self.auto_venc_cbtext,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(self.auto_aenc_cbtext, 4, 3, 1, 1)
        input_grid.attach_next_to(auto_aconf_button, self.auto_aenc_cbtext,
                                  Gtk.PositionType.RIGHT, 1, 1)
        input_grid.attach(self.auto_queue_button, 4, 4, 2, 1)
        input_grid.attach(hsep, 0, 5, 6, 1)

        auto_scrwin = Gtk.ScrolledWindow()
        auto_scrwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        #auto_scrwin.set_overlay_scrolling(False)
        #(enable, enable_edit, encode, encode_edit, type, codec, name, 
        # language)
        self.auto_lstore = Gtk.ListStore(bool, bool, bool, bool, str, str, str,
                                         str)

        auto_tview = Gtk.TreeView(self.auto_lstore)
        auto_scrwin.add(auto_tview)

        enable_crtoggle = Gtk.CellRendererToggle()
        enable_tvcolumn = Gtk.TreeViewColumn('Enable', enable_crtoggle,
                                             active=0, activatable=1)
        enable_crtoggle.connect('toggled', self.on_cell_toggled, 0)
        auto_tview.append_column(enable_tvcolumn)

        encode_crtoggle = Gtk.CellRendererToggle()
        encode_tvcolumn = Gtk.TreeViewColumn('Encode', encode_crtoggle,
                                             active=2, activatable=3)
        encode_crtoggle.connect('toggled', self.on_cell_toggled, 2)
        auto_tview.append_column(encode_tvcolumn)

        codec_crtext = Gtk.CellRendererText()
        codec_crtext.set_sensitive(False)
        codec_tvcolumn = Gtk.TreeViewColumn('Codec', codec_crtext, text=5)
        auto_tview.append_column(codec_tvcolumn)

        name_crtext = Gtk.CellRendererText()
        name_crtext.set_property('editable', True)
        name_tvcolumn = Gtk.TreeViewColumn('Name', name_crtext, text=6)
        name_tvcolumn.set_expand(True)
        name_crtext.connect('edited', self.on_cell_edited, 6)
        auto_tview.append_column(name_tvcolumn)

        lang_crtext = Gtk.CellRendererText()
        lang_crtext.set_property('editable', True)
        lang_tvcolumn = Gtk.TreeViewColumn('Language', lang_crtext, text=7)
        lang_crtext.connect('edited', self.on_cell_edited, 7)
        auto_tview.append_column(lang_tvcolumn)

        input_box.pack_start(input_grid, False, False, 0)
        input_box.pack_start(auto_scrwin, True, True, 0)

        #--Queue--#
        self.queue_tstore = Gtk.TreeStore(GObject.TYPE_PYOBJECT, str, str, str)
        # Do one encoding task at a time
        self.worker = ThreadPoolExecutor(max_workers=1)
        # Lock the worker thread
        self.idle = True
        self.lock = Lock()
        self.lock.acquire()

        queue_scrwin = Gtk.ScrolledWindow()
        queue_scrwin.set_policy(Gtk.PolicyType.AUTOMATIC,
                                Gtk.PolicyType.ALWAYS)
        queue_tview = Gtk.TreeView(self.queue_tstore)
        self.queue_tselection = queue_tview.get_selection()
        queue_scrwin.add(queue_tview)

        qexp_crpixbuf = Gtk.CellRendererPixbuf()
        qexp_crpixbuf.set_property('is-expander', True)
        qexp_tvcolumn = Gtk.TreeViewColumn('', qexp_crpixbuf)
        queue_tview.append_column(qexp_tvcolumn)

        qsrc_crtext = Gtk.CellRendererText()
        qsrc_tvcolumn = Gtk.TreeViewColumn('Source', qsrc_crtext, text=1)
        queue_tview.append_column(qsrc_tvcolumn)

        qcod_crtext = Gtk.CellRendererText()
        qcod_tvcolumn = Gtk.TreeViewColumn('Codec', qcod_crtext, text=2)
        queue_tview.append_column(qcod_tvcolumn)

        qsta_crtext = Gtk.CellRendererText()
        qsta_tvcolumn = Gtk.TreeViewColumn('Status', qsta_crtext, text=3)
        queue_tview.append_column(qsta_tvcolumn)

        queue_start_button = Gtk.Button()
        queue_start_button.set_label('Start')
        queue_start_button.connect('clicked', self.on_start_clicked)
        queue_stop_button = Gtk.Button()
        queue_stop_button.set_label('Stop')
        queue_stop_button.connect('clicked', self.on_stop_clicked)
        queue_del_button = Gtk.Button()
        queue_del_button.set_label('Delete')
        queue_del_button.connect('clicked', self.on_del_clicked)
        queue_clr_button = Gtk.Button()
        queue_clr_button.set_label('Clear')
        queue_clr_button.connect('clicked', self.on_clr_clicked)

        queue_ctl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                spacing=6)
        queue_ctl_box.pack_start(queue_start_button, True, True, 0)
        queue_ctl_box.pack_start(queue_stop_button, True, True, 0)
        queue_ctl_box.pack_start(queue_del_button, True, True, 0)
        queue_ctl_box.pack_start(queue_clr_button, True, True, 0)

        queue_box.pack_start(queue_scrwin, True, True, 0)
        queue_box.pack_start(queue_ctl_box, False, True, 0)

        #--Progress Bar--#
        self.pbar = Gtk.ProgressBar()
        self.pbar.set_property('margin', 6)
        self.pbar.set_text('Ready')
        self.pbar.set_show_text(True)

        main_box.pack_start(self.pbar, False, True, 0)

        self.add(main_box)

        #--Encoders--#
        for x in VENCS:
            self.venc_cbtext.append_text(x)
            self.venc_cbtext.set_active(0)
            self.auto_venc_cbtext.append_text(x)
            self.auto_venc_cbtext.set_active(0)
        for x in AENCS:
            self.aenc_cbtext.append_text(x)
            self.aenc_cbtext.set_active(0)
            self.auto_aenc_cbtext.append_text(x)
            self.auto_aenc_cbtext.set_active(0)

        #--Dialogs--#
        if 'fdkaac' in AENCS:
            self.fdkaac_dlg = EncoderDialog(self, 'fdkaac')
            self.fdkaac_dlg.hide()
        if 'lame' in AENCS:
            self.lame_dlg = EncoderDialog(self, 'lame')
            self.lame_dlg.hide()
        if 'x264' in VENCS:
            self.x264_dlg = EncoderDialog(self, 'x264')
            self.x264_dlg.hide()
        if 'x265' in VENCS:
            self.x265_dlg = EncoderDialog(self, 'x265')
            self.x265_dlg.hide()

        self.about_dlg = AboutDialog(self)
        self.about_dlg.set_transient_for(self)

    def on_sccr_clicked(self, button):
        sccr_win.show_all()

    def on_ched_clicked(self, button):
        ched_win.show_all()

    def on_about_clicked(self, button):
        self.about_dlg.run()
        self.about_dlg.hide()

    def on_cell_toggled(self, crtoggle, path, i):
        self.auto_lstore[path][i] = not self.auto_lstore[path][i]

    def on_cell_edited(self, crtext, path, t, i):
        # Language is a 3 letter code
        # TODO: write a custom cell renderer for this
        if i == 4:
            t = t[:3]
        self.auto_lstore[path][i] = t

    def on_vsrc_file_set(self, button):
        self.vqueue_button.set_sensitive(True)

    def on_vqueue_clicked(self, button):
        self.worker.submit(self._wait)
        x = self.venc_cbtext.get_active_text()
        s = self.vsrc_fcbutton.get_filename()
        wd, f = os.path.split(s)
        if not os.path.isdir(wd + '/out'):
            os.mkdir(wd + '/out')
        d = wd + '/out/' + os.path.splitext(f)[0]
        if x == 'x264':
            dp = int(conf.x264_depth_cbtext.get_active_text())
            q = conf.x264_quality_spin.get_value_as_int()
            p = conf.x264_preset_cbtext.get_active_text()
            if p == 'none':
                p = ''
            t = conf.x264_tune_cbtext.get_active_text()
            if t == 'none':
                t = ''
            c = conf.x264_cont_cbtext.get_active_text()
            future = self.worker.submit(self._x264, s, d, dp, q, p, t, c)
        elif x == 'x265':
            dp = int(conf.x265_depth_cbtext.get_active_text())
            q = conf.x265_quality_spin.get_value_as_int()
            p = conf.x265_preset_cbtext.get_active_text()
            if p == 'none':
                p = ''
            t = conf.x265_tune_cbtext.get_active_text()
            if t == 'none':
                t = ''
            c = conf.x265_cont_cbtext.get_active_text()
            future = self.worker.submit(self._x265, s, d, dp, q, p, t, c)
        self.queue_tstore.append(None, [future, f, x, 'Waiting'])
        self.worker.submit(self._update_queue)

    def on_asrc_file_set(self, button):
        self.aqueue_button.set_sensitive(True)

    def on_aqueue_clicked(self, button):
        self.worker.submit(self._wait)
        x = self.aenc_cbtext.get_active_text()
        s = self.asrc_fcbutton.get_filename()
        wd, f = os.path.split(s)
        if not os.path.isdir(wd + '/out'):
            os.mkdir(wd + '/out')
        d = wd + '/out/' + os.path.splitext(f)[0]
        if x == 'fdkaac':
            m = conf.fdkaac_mode_cbtext.get_active_text()
            b = conf.fdkaac_bitrate_spin.get_value_as_int()
            q = conf.fdkaac_quality_spin.get_value_as_int()
            c = conf.fdkaac_cont_cbtext.get_active_text()
            future = self.worker.submit(self._fdkaac, s, d, m, b, q, c)
        elif x == 'lame':
            m = conf.lame_mode_cbtext.get_active_text()
            b = conf.lame_bitrate_spin.get_value_as_int()
            q = conf.lame_quality_spin.get_value_as_int()
            future = self.worker.submit(self._lame, s, d, m, b, q)
        self.queue_tstore.append(None, [future, f, x, 'Waiting'])
        self.worker.submit(self._update_queue)

    def on_auto_src_file_set(self, button):
        wd = button.get_filename()
        self.sources = []
        self.data = []
        self.auto_lstore.clear()

        # Keep MKVs only (for now?)
        for f in os.listdir(wd):
            if re.search('\.mkv$', f):
                f = wd + '/' + f
                self.sources.append(f)

        # Get source infos
        for i in range(len(self.sources)):
            s = self.sources[i]
            d = MatroskaOps(s).get_data()
            self.data.append(d)

        # Pick reference tracks
        tracks_ref = self.data[0]

        # Make sure tracks are identical across files
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO,
                                   Gtk.ButtonsType.OK, 'Track Mismatch')

        for i in range(1, len(self.data)):
            tracks = self.data[i]
            o = os.path.basename(self.sources[0])
            f = os.path.basename(self.sources[i])

            if len(tracks) != len(tracks_ref):
                t = ('{} ({} tracks) and {} ({} tracks) differ from each '
                     'other. Please make sure all files share the same '
                     'layout.'
                    ).format(o, str(len(tracks_ref)), f, str(len(tracks)))

                dialog.format_secondary_text(t)
                dialog.run()

            # -1 because there is a 'uid' entry
            for j in range(len(tracks) - 1):
                k = 'track' + str(j)
                codec_ref = tracks_ref[k]['codec']
                lang_ref = tracks_ref[k].get('lang', '')
                channels_ref = tracks_ref[k].get('channels', '')
                codec = tracks[k]['codec']
                lang = tracks[k].get('lang', '')
                channels = tracks[k].get('channels', '')

                if codec != codec_ref:
                    t = ('{} (track {}: {}) and {} (track {}: {}) have '
                         'different codecs. Please make sure all files '
                         'share the same layout.'
                        ).format(o, str(j), codec_ref, f, str(j), codec)

                    dialog.format_secondary_text(t)
                    dialog.run()

                elif lang != lang_ref:
                    t = ('{} (track {}: {}) and {} (track {}: {}) have '
                         'different languages. Please make sure all files '
                         'share the same layout.'
                        ).format(o, str(j), lang_ref, f, str(j), lang)

                    dialog.format_secondary_text(t)
                    dialog.run()

                elif channels != channels_ref:
                    t = ('{} (track {}: {}) and {} (track {}: {}) have '
                         'different channels. Please make sure all files '
                         'share the same layout.'
                        ).format(o, str(j), channels_ref, f, str(j), channels)

                    dialog.format_secondary_text(t)
                    dialog.run()

                dialog.hide()

        dialog.destroy()

        # -1 because there is a 'uid' entry
        for i in range(len(tracks_ref) - 1):
            track = tracks_ref['track' + str(i)]
            enable = True
            enable_edit = True
            encode = True
            encode_edit = True
            type = ''
            codec = track['codec']
            name = track.get('name', '')
            lang = track.get('lang', 'und')

            if codec in VTYPES:
                type = 'video'
                codec = VTYPES[codec]
                enable_edit = False
            elif codec in ATYPES:
                type = 'audio'
                channels = track.get('channels', '')
                if channels == '1':
                    channels = '1.0'
                elif channels == '2':
                    channels = '2.0'
                elif channels == '5':
                    channels = '5.0'
                elif channels == '6':
                    channels = '5.1'
                elif channels == '7':
                    channels = '6.1'
                elif channels == '8':
                    channels = '7.1'
                if channels:
                    codec = ATYPES[codec] + ' ' + channels
                else:
                    codec = ATYPES[codec]
            elif codec in STYPES:
                type = 'subtitle'
                codec = STYPES[codec]
                encode = False
                encode_edit = False

            self.auto_lstore.append([enable, enable_edit, encode,
                                     encode_edit, type, codec, name, lang])

        self.auto_queue_button.set_sensitive(True)

    def on_auto_queue_clicked(self, button):
        wd = self.auto_src_fcbutton.get_filename()
        if not os.path.isdir(wd + '/out'):
            os.mkdir(wd + '/out')

        for i in range(len(self.sources)):
            self.worker.submit(self._wait)
            vtrack = []
            atracks = []
            stracks = []
            source = self.sources[i]
            filename = os.path.basename(source)
            destination = wd + '/out/' + filename
            basename, extension = os.path.splitext(filename)
            extension = extension.strip('.')
            uid = self.data[i]['uid']
            job = self.queue_tstore.append(None, [None, filename, '',
                                                  'Waiting'])
            for j in range(len(self.auto_lstore)):
                #(enable, enable_edit, encode, encode_edit, type, codec, name,
                # language)
                # track = [id, filename, extension, name, language, encode]
                track = self.auto_lstore[j]
                enable = track[0]
                encode = track[2]
                type = track[4]
                codec = track[5]
                name = track[6]
                lang = track[7]
                if type == 'video' and enable:
                    f = wd + '/out/' + basename
                    e = extension
                    vtrack = [j, f, e, name, lang, encode]
                if type == 'audio' and enable:
                    if encode:
                        f = wd + '/out/' + basename + '_' + str(j)
                        e = codec.split(' ')[0]
                    else:
                        f = wd + '/' + basename
                        e = extension
                    atracks.append([j, f, e, name, lang, encode])
                if type == 'subtitle' and enable:
                    f = wd + '/out/' + basename
                    e = extension
                    stracks.append([j, f, e, name, lang, encode])

            # Create VapourSynth script
            if vtrack[5]:
                vtrack[0] = 0
                fps = []
                if conf.fps_check.get_active():
                    fn = conf.fpsnum_spin.get_value_as_int()
                    fd = conf.fpsden_spin.get_value_as_int()
                    fps = [fn, fd]
                crop = []
                if conf.crop_check.get_active():
                    cl = conf.lcrop_spin.get_value_as_int()
                    cr = conf.rcrop_spin.get_value_as_int()
                    ct = conf.tcrop_spin.get_value_as_int()
                    cb = conf.bcrop_spin.get_value_as_int()
                    crop = [cl, cr, ct, cb]
                resize = []
                if conf.resize_check.get_active():
                    rw = conf.wresize_spin.get_value_as_int()
                    rh = conf.hresize_spin.get_value_as_int()
                    rf = conf.resize_cbtext.get_active_text()
                    resize = [rw, rh, rf]
                sdenoise = []
                if conf.sdenoise_check.get_active():
                    sdf = conf.sdenoise_cbtext.get_active_text()
                    if sdf == 'RemoveGrain':
                        rgm = [conf.rgvs_mode_spin.get_value_as_int()]
                        if conf.rgvs_adv_check.get_active():
                            rgm.append(rgvs_umode_spin.get_value_as_int())
                            rgm.append(rgvs_vmode_spin.get_value_as_int())
                        sdenoise = [sdf, rgm]
                tdenoise = []
                if conf.tdenoise_check.get_active():
                    tdf = conf.tdenoise_cbtext.get_active_text()
                    if tdf == 'TemporalSoften':
                        tsr = conf.tsoft_rad_spin.get_value_as_int()
                        tsl = conf.tsoft_lt_spin.get_value_as_int()
                        tsc = conf.tsoft_ct_spin.get_value_as_int()
                        tss = conf.tsoft_sc_spin.get_value_as_int()
                        tdenoise = [tdf, tsr, tsl, tsc, tss]
                    elif tdf == 'FluxSmoothT':
                        fst = conf.fsmooth_tt_spin.get_value_as_int()
                        fsp = []
                        if conf.fsmooth_y_check.get_active():
                            fsp.append(0)
                        if conf.fsmooth_u_check.get_active():
                            fsp.append(1)
                        if conf.fsmooth_v_check.get_active():
                            fsp.append(2)
                        tdenoise = [tdf, fst, fsp]
                stdenoise = []
                if conf.stdenoise_check.get_active():
                    stdf = conf.stdenoise_cbtext.get_active_text()
                    if stdf == 'FluxSmoothST':
                        fst = conf.fsmooth_tt_spin.get_value_as_int()
                        fss = conf.fsmooth_st_spin.get_value_as_int()
                        fsp = []
                        if conf.fsmooth_y_check.get_active():
                            fsp.append(0)
                        if conf.fsmooth_u_check.get_active():
                            fsp.append(1)
                        if conf.fsmooth_v_check.get_active():
                            fsp.append(2)
                        stdenoise = [stdf, fst, fss, fsp]
                deband = []
                if conf.deband_check.get_active():
                    df = conf.deband_cbtext.get_active_text()
                    if df == 'f3kdb':
                        fpr = conf.f3kdb_preset_cbtext.get_active_text()
                        fpl = conf.f3kdb_plane_cbtext.get_active_text()
                        fdp = conf.f3kdb_depth_spin.get_value_as_int()
                        if fpl in ['luma', 'chroma']:
                            fpr = fpr + '/' + fpl
                        if not conf.f3kdb_grain_check.get_active():
                            fpr = fpr + '/nograin'
                        deband = [df, fpr, fdp]

                vpy = wd + '/out/' + basename + '.vpy'

                self.worker.submit(self._vpy, source, vpy, fps, crop, resize,
                                   sdenoise, tdenoise, stdenoise, deband)

                # Encode video
                x = self.auto_venc_cbtext.get_active_text()
                if x == 'x264':
                    dp = int(conf.x264_depth_cbtext.get_active_text())
                    q = conf.x264_quality_spin.get_value_as_int()
                    p = conf.x264_preset_cbtext.get_active_text()
                    if p == 'none':
                        p = ''
                    t = conf.x264_tune_cbtext.get_active_text()
                    if t == 'none':
                        t = ''
                    c = conf.x264_cont_cbtext.get_active_text()
                    vtrack[2] = c

                    future = self.worker.submit(self._x264, vpy, vtrack[1], dp,
                                                q, p, t, c)
                if x == 'x265':
                    dp = int(conf.x265_depth_cbtext.get_active_text())
                    q = conf.x265_quality_spin.get_value_as_int()
                    p = conf.x265_preset_cbtext.get_active_text()
                    if p == 'none':
                        p = ''
                    t = conf.x265_tune_cbtext.get_active_text()
                    if t == 'none':
                        t = ''
                    c = conf.x265_cont_cbtext.get_active_text()
                    vtrack[2] = c

                    future = self.worker.submit(self._x265, vpy, vtrack[1], dp,
                                                q, p, t, c)

                self.queue_tstore.append(job, [future, '', x, 'Waiting'])

            # Extract audio
            tracks = []
            for track in atracks:
                if track[5]:
                    tracks.append(track)

            future = self.worker.submit(self._extract, source, tracks)

            self.queue_tstore.append(job, [future, '', 'extract',
                                           'Waiting'])

            # Encode audio
            for track in atracks:
                if track[5]:
                    x = self.auto_aenc_cbtext.get_active_text()
                    a = track[1] + '.' + track[2]
                    if x == 'fdkaac':
                        m = conf.fdkaac_mode_cbtext.get_active_text()
                        b = conf.fdkaac_bitrate_spin.get_value_as_int()
                        q = conf.fdkaac_quality_spin.get_value_as_int()
                        c = conf.fdkaac_cont_cbtext.get_active_text()

                        future = self.worker.submit(self._fdkaac, a, track[1],
                                                    m, b, q, c)

                    elif x == 'lame':
                        m = conf.lame_mode_cbtext.get_active_text()
                        b = conf.lame_bitrate_spin.get_value_as_int()
                        q = conf.lame_quality_spin.get_value_as_int()

                        future = self.worker.submit(self._lame, a, track[1], m,
                                                    b, q)

                    self.queue_tstore.append(job, [future, '', x, 'Waiting'])

            # Merge tracks
            future = self.worker.submit(self._merge, source, destination,
                                        vtrack, atracks, stracks, uid)

            self.queue_tstore.append(job, [future, '', 'merge', 'Waiting'])

            # Clean up
            self.worker.submit(self._clean, wd)

            self.worker.submit(self._update_queue)

    def on_conf_clicked(self, button, m, t):
        if m == 'manual':
            if t == 'video':
                x = self.venc_cbtext.get_active_text()
            elif t == 'audio':
                x = self.aenc_cbtext.get_active_text()
        elif m == 'auto':
            if t == 'video':
                x = self.auto_venc_cbtext.get_active_text()
            elif t == 'audio':
                x = self.auto_aenc_cbtext.get_active_text()

        if x == 'fdkaac':
            self.fdkaac_dlg.run()
            self.fdkaac_dlg.hide()
        elif x == 'lame':
            self.lame_dlg.run()
            self.lame_dlg.hide()
        elif x in ['x264', 'x264-10bit']:
            self.x264_dlg.run()
            self.x264_dlg.hide()
        elif x in ['x265', 'x265-10bit']:
            self.x265_dlg.run()
            self.x265_dlg.hide()

    def on_auto_sconf_clicked(self, button):
        vs_dlg.set_transient_for(win)
        vs_dlg.run()
        vs_dlg.hide()

    def on_start_clicked(self, button):
        if len(self.queue_tstore):
            print('Start processing...')
            self.idle = False
            self.lock.release()

    def on_stop_clicked(self, button):
        if not self.idle:
            print('Stop processing...')
            self.idle = True
            # Wait for the process to terminate
            while self.proc.poll() == None:
                self.proc.terminate()

            njobs = len(self.queue_tstore)
            for i in range(njobs):
                path = Gtk.TreePath(i)
                job = self.queue_tstore.get_iter(path)
                status = self.queue_tstore.get_value(job, 3)
                if status == 'Running':
                    if self.queue_tstore.iter_has_child(job):
                        nsteps = self.queue_tstore.iter_n_children(job)
                        for j in range(nsteps):
                            path = Gtk.TreePath([i, j])
                            step = self.queue_tstore.get_iter(path)
                            future = self.queue_tstore.get_value(step, 0)
                            # Mark children as failed
                            self.queue_tstore.set_value(step, 3, 'Failed')
                            # Cancel pending children
                            if not future.done():
                                future.cancel()
                    # Mark job as failed
                    self.queue_tstore.set_value(job, 3, 'Failed')

            self.pbar.set_fraction(0)
            self.pbar.set_text('Ready')

    def on_del_clicked(self, button):
        job = self.queue_tselection.get_selected()[1]
        if job != None:
            # If child, select parent instead
            if self.queue_tstore.iter_depth(job) == 1:
                job = self.queue_tstore.iter_parent(job)
            # If parent, delete all children
            if self.queue_tstore.iter_has_child(job):
                nsteps = self.queue_tstore.iter_n_children(job)
                for i in range(nsteps):
                    step = self.queue_tstore.iter_nth_child(job, 0)
                    future = self.queue_tstore.get_value(step, 0)
                    # Cancel and delete child only if not running
                    if not future.running():
                        future.cancel()
                        self.queue_tstore.remove(step)
                # Delete parent only when all children are
                if not self.queue_tstore.iter_has_child(job):
                    self.queue_tstore.remove(job)
            else:
                future = self.queue_tstore.get_value(job, 0)
                # Cancel and delete job only if not running
                if not future.running():
                    future.cancel()
                    self.queue_tstore.remove(job)

    def on_clr_clicked(self, button):
        # Don't clear when jobs are running
        if self.idle:
            njobs = len(self.queue_tstore)
            for i in range(njobs):
                path = Gtk.TreePath(i)
                job = self.queue_tstore.get_iter(path)
                # Clear children before parents
                if self.queue_tstore.iter_has_child(job):
                    nsteps = self.queue_tstore.iter_n_children(job)
                    for j in range(nsteps):
                        path = Gtk.TreePath([i, j])
                        step = self.queue_tstore.get_iter(path)
                        future = self.queue_tstore.get_value(step, 0)
                        # Cancel pending children before deleting them
                        if not future.done():
                            future.cancel()
                else:
                    future = self.queue_tstore.get_value(job, 0)
                    # Cancel pending jobs before deleting them
                    if not future.done():
                        future.cancel()
            # Clear queue
            self.queue_tstore.clear()

    def _wait(self):
        if self.idle:
            self.lock.acquire()
        else:
            self.lock.release()

    def _update_queue(self):
        njobs = len(self.queue_tstore)
        for i in range(njobs):
            path = Gtk.TreePath(i)
            job = self.queue_tstore.get_iter(path)
            future = self.queue_tstore.get_value(job, 0)
            status = self.queue_tstore.get_value(job, 3)
            if self.queue_tstore.iter_has_child(job):
                nsteps = self.queue_tstore.iter_n_children(job)
                for j in range(nsteps):
                    path = Gtk.TreePath([i, j])
                    step = self.queue_tstore.get_iter(path)
                    future = self.queue_tstore.get_value(step, 0)
                    status = self.queue_tstore.get_value(step, 3)
                    # Mark done children as such
                    if future.done() and status != 'Failed':
                        GLib.idle_add(self.queue_tstore.set_value, step, 3,
                                      'Done')
                        # Mark parent as done if all children are
                        if j == nsteps - 1:
                            GLib.idle_add(self.queue_tstore.set_value, job, 3,
                                          'Done')
                            # Mark as idle if child was the last job
                            if i == njobs - 1:
                                self.idle = True
                                self.lock.acquire()
                    # Mark running child as such
                    elif future.running():
                        GLib.idle_add(self.queue_tstore.set_value, step, 3,
                                      'Running')
                        # Mark parent as running if a child is
                        GLib.idle_add(self.queue_tstore.set_value, job, 3,
                                      'Running')
            else:
                # Mark done jobs as such
                if future.done() and status != 'Failed':
                    GLib.idle_add(self.queue_tstore.set_value, job, 3,
                                  'Done')
                    # Mark as idle if job was the last
                    if i == njobs - 1:
                        self.idle = True
                        self.lock.acquire()
                # Mark running job as such
                elif future.running():
                    GLib.idle_add(self.queue_tstore.set_value, job, 3,
                                  'Running')

    def _extract(self, source, tracks):
        print('Extract...')
        self._update_queue()
        cmd = MatroskaOps(source).extract(tracks)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                     universal_newlines=True)
        self._mkvtoolnix_progress('x')

    def _merge(self, source, dest, vtrack, atracks, stracks, uid):
        print('Merge...')
        self._update_queue()
        # Put that here until I find a way to do it in on_auto_queue_clicked.
        for track in atracks:
            if track[5]:
                track[0] = 0
                x = self.auto_aenc_cbtext.get_active_text()
                if x == 'fdkaac':
                    c = conf.fdkaac_cont_cbtext.get_active_text()
                    track[2] = c
                elif x == 'lame':
                    track[2] = 'mp3'

        cmd = MatroskaOps(source).merge(dest, vtrack, atracks, stracks, uid)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                     universal_newlines=True)
        self._mkvtoolnix_progress('m')

    def _clean(self, directory):
        print('Clean leftovers...')
        for f in os.listdir(directory):
            if re.search('\.ffindex$', f):
                os.remove(directory + '/' + f)
        directory = directory + '/out'
        for f in os.listdir(directory):
            if not re.search('\.mkv$', f):
                os.remove(directory + '/' + f)

        Glid.add(self.pbar.set_fraction, 0)
        Glib.add(self.pbar.set_text, 'Ready')

    def _vpy(self, source, destination, fps, crop, resize, sdenoise, tdenoise,
             stdenoise, deband):
        print('Create VapourSynth script...')
        v = Encode(source).vpy(fps, crop, resize, sdenoise, tdenoise,
                               stdenoise, deband)

        print('Write ' + destination)
        with open(destination, 'w') as f:
            f.write(v)

    def _info(self, source):
        cmd = Encode(source).info()
        self.proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                     universal_newlines=True)
        GLib.idle_add(self.pbar.set_fraction, 0)
        GLib.idle_add(self.pbar.set_text, 'Encoding video...')
        while self.proc.poll() == None:
            line = self.proc.stdout.readline()
            # Get the frame total
            if 'Frames:' in line:
                d = int(line.split(' ')[1])
        return d

    def _x264(self, source, dest, depth, quality, preset, tune, container):
        print('Encode video...')
        self._update_queue()
        d = self._info(source)
        cmd = Encode(source).x264(dest, depth, quality, preset, tune,
                                  container)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._video_progress(d)

    def _x265(self, source, dest, depth, quality, preset, tune, container):
        print('Encode video...')
        self._update_queue()
        d = self._info(source)
        cmd = Encode(source).x265(dest, depth, quality, preset, tune,
                                  container)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._video_progress(d)

    def _fdkaac(self, source, dest, mode, bitrate, quality, container):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(source).fdkaac(dest, mode, bitrate, quality, container)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _lame(self, source, dest, mode, bitrate, quality):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(source).lame(dest, mode, bitrate, quality)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _mkvtoolnix_progress(self, mode):
        GLib.idle_add(self.pbar.set_fraction, 0)
        if mode == 'x':
            GLib.idle_add(self.pbar.set_text, 'Extracting tracks...')
        elif mode == 'm':
            GLib.idle_add(self.pbar.set_text, 'Merging tracks...')
        while self.proc.poll() == None:
            line = self.proc.stdout.readline()
            if 'Progress:' in line:
                f = int(re.findall('[0-9]+', line)[0]) / 100
                GLib.idle_add(self.pbar.set_fraction, f)
        if self.proc.poll() < 0:
            GLib.idle_add(self.pbar.set_text, 'Failed')
        else:
            GLib.idle_add(self.pbar.set_text, 'Ready')
        GLib.idle_add(self.pbar.set_fraction, 0)

    def _video_progress(self, duration):
        while self.proc.poll() == None:
            line = self.proc.stderr.readline()
            # Get the current frame
            if re.match('^[0-9]+ ', line):
                position = int(line.split(' ')[0])
                f = round(position / duration, 2)
                GLib.idle_add(self.pbar.set_fraction, f)
        if self.proc.poll() < 0:
            GLib.idle_add(self.pbar.set_text, 'Failed')
        else:
            GLib.idle_add(self.pbar.set_text, 'Ready')
        GLib.idle_add(self.pbar.set_fraction, 0)

    def _audio_progress(self):
        GLib.idle_add(self.pbar.set_fraction, 0)
        GLib.idle_add(self.pbar.set_text, 'Encoding audio...')
        while self.proc.poll() == None:
            line = self.proc.stderr.readline()
            # Get the clip duration
            if 'Duration:' in line:
                d = re.findall('[0-9]{2}:[0-9]{2}:[0-9]{2}', line)[0]
                h, m, s = d.split(':')
                d = int(h) * 3600 + int(m) * 60 + int(s)
            # Get the current timestamp
            if 'time=' in line:
                p = re.findall('[0-9]{2}:[0-9]{2}:[0-9]{2}', line)[0]
                h, m, s = p.split(':')
                p = int(h) * 3600 + int(m) * 60 + int(s)
                f = round(p / d, 2)
                GLib.idle_add(self.pbar.set_fraction, f)
        if self.proc.poll() < 0:
            GLib.idle_add(self.pbar.set_text, 'Failed')
        else:
            GLib.idle_add(self.pbar.set_text, 'Ready')
        GLib.idle_add(self.pbar.set_fraction, 0)

class ChapterEditorWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title='pyanimchap')
        self.set_default_size(640, 520)

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
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        scrwin.set_overlay_scrolling(False)
        scrwin.add(vport)

        self.add(scrwin)

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
        fpsnum_adj = Gtk.Adjustment(0, 0, 120000, 1, 10)
        fpsnum_spin = Gtk.SpinButton()
        fpsnum_spin.set_numeric(True)
        fpsnum_spin.set_adjustment(fpsnum_adj)
        fpsnum_spin.set_property('hexpand', True)
        fpsnum_spin.set_value(self.fpsnum)
        fpsden_adj = Gtk.Adjustment(0, 1000, 1001, 1, 1)
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
            self.box.show_all()

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

class ScriptCreatorWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title='pyanimscript')
        self.set_default_size(640, 520)

        self.source = ''

        #--Header Bar--#
        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.set_property('title', 'pyanimscript')

        open_button = Gtk.Button('Open')
        open_button.connect('clicked', self.on_open_clicked)
        save_button = Gtk.Button('Save')
        save_button.connect('clicked', self.on_save_clicked)

        settings_button = Gtk.Button()
        settings_icon = Gio.ThemedIcon(name='applications-system-symbolic')
        settings_image = Gtk.Image.new_from_gicon(settings_icon,
                                                  Gtk.IconSize.BUTTON)
        settings_button.set_image(settings_image)
        settings_button.connect('clicked', self.on_settings_clicked)

        hbar.pack_start(open_button)
        hbar.pack_start(save_button)
        hbar.pack_end(settings_button)

        self.set_titlebar(hbar)

        #--Open/Save--#
        self.open_fcdlg = Gtk.FileChooserDialog('Open Video File', self,
                                                Gtk.FileChooserAction.OPEN,
                                                ('Cancel',
                                                 Gtk.ResponseType.CANCEL,
                                                 'Open', Gtk.ResponseType.OK))
        self.open_fcdlg.add_filter(vflt)
        self.save_fcdlg = Gtk.FileChooserDialog('Save VapourSynth Script',
                                                self,
                                                Gtk.FileChooserAction.SAVE,
                                                ('Cancel',
                                                 Gtk.ResponseType.CANCEL,
                                                 'Save', Gtk.ResponseType.OK))
        self.save_fcdlg.add_filter(sflt)

        #--Textview--#
        self.tbuffer = Gtk.TextBuffer()
        tview = Gtk.TextView()
        tview.set_buffer(self.tbuffer)
        tview.set_left_margin(6)
        tview.set_right_margin(6)

        self.add(tview)

    def _update_buffer(self):
        fps = []
        if conf.fps_check.get_active():
            fn = conf.fpsnum_spin.get_value_as_int()
            fd = conf.fpsden_spin.get_value_as_int()
            fps = [fn, fd]
        crop = []
        if conf.crop_check.get_active():
            cl = conf.lcrop_spin.get_value_as_int()
            cr = conf.rcrop_spin.get_value_as_int()
            ct = conf.tcrop_spin.get_value_as_int()
            cb = conf.bcrop_spin.get_value_as_int()
            crop = [cl, cr, ct, cb]
        resize = []
        if conf.resize_check.get_active():
            rw = conf.wresize_spin.get_value_as_int()
            rh = conf.hresize_spin.get_value_as_int()
            rf = conf.resize_cbtext.get_active_text()
            resize = [rw, rh, rf]
        sdenoise = []
        if conf.sdenoise_check.get_active():
            sdf = conf.sdenoise_cbtext.get_active_text()
            if sdf == 'RemoveGrain':
                rgm = [conf.rgvs_mode_spin.get_value_as_int()]
                if conf.rgvs_adv_check.get_active():
                    rgm.append(rgvs_umode_spin.get_value_as_int())
                    rgm.append(rgvs_vmode_spin.get_value_as_int())
                sdenoise = [sdf, rgm]
        tdenoise = []
        if conf.tdenoise_check.get_active():
            tdf = conf.tdenoise_cbtext.get_active_text()
            if tdf == 'TemporalSoften':
                tsr = conf.tsoft_rad_spin.get_value_as_int()
                tsl = conf.tsoft_lt_spin.get_value_as_int()
                tsc = conf.tsoft_ct_spin.get_value_as_int()
                tss = conf.tsoft_sc_spin.get_value_as_int()
                tdenoise = [tdf, tsr, tsl, tsc, tss]
            elif tdf == 'FluxSmoothT':
                fst = conf.fsmooth_tt_spin.get_value_as_int()
                fsp = []
                if conf.fsmooth_y_check.get_active():
                    fsp.append(0)
                if conf.fsmooth_u_check.get_active():
                    fsp.append(1)
                if conf.fsmooth_v_check.get_active():
                    fsp.append(2)
                tdenoise = [tdf, fst, fsp]
        stdenoise = []
        if conf.stdenoise_check.get_active():
            stdf = conf.stdenoise_cbtext.get_active_text()
            if stdf == 'FluxSmoothST':
                fst = conf.fsmooth_tt_spin.get_value_as_int()
                fss = conf.fsmooth_st_spin.get_value_as_int()
                fsp = []
                if conf.fsmooth_y_check.get_active():
                    fsp.append(0)
                if conf.fsmooth_u_check.get_active():
                    fsp.append(1)
                if conf.fsmooth_v_check.get_active():
                    fsp.append(2)
                stdenoise = [stdf, fst, fss, fsp]
        deband = []
        if conf.deband_check.get_active():
            df = conf.deband_cbtext.get_active_text()
            if df == 'f3kdb':
                fpr = conf.f3kdb_preset_cbtext.get_active_text()
                fpl = conf.f3kdb_plane_cbtext.get_active_text()
                fdp = conf.f3kdb_depth_spin.get_value_as_int()
                if fpl in ['luma', 'chroma']:
                    fpr = fpr + '/' + fpl
                if not conf.f3kdb_grain_check.get_active():
                    fpr = fpr + '/nograin'
                deband = [df, fpr, fdp]

        s = Encode(self.source).vpy(fps, crop, resize, sdenoise, tdenoise,
                                    stdenoise, deband)
        self.tbuffer.set_text(s)

    def on_open_clicked(self, button):
        response = self.open_fcdlg.run()

        if response == Gtk.ResponseType.OK:
            self.source = self.open_fcdlg.get_filename()

            self._update_buffer()

        self.open_fcdlg.hide()

    def on_save_clicked(self, button):
        o = os.path.splitext(self.source)[0] + '.vpy'
        self.save_fcdlg.set_filename(o)

        response = self.save_fcdlg.run()

        if response == Gtk.ResponseType.OK:
            o = self.save_fcdlg.get_filename()
            if not re.search('\.vpy$', o):
                o = o + '.vpy'

            s = self.tbuffer.get_text(self.tbuffer.get_start_iter(),
                                      self.tbuffer.get_end_iter(),
                                      include_hidden_chars=True)

            with open(o, 'w') as f:
                f.write(s)

        self.save_fcdlg.hide()

    def on_settings_clicked(self, button):
        vs_dlg.set_transient_for(sccr_win)
        vs_dlg.run()
        if self.source:
            self._update_buffer()
        vs_dlg.hide()

class EncoderDialog(Gtk.Dialog):

    def __init__(self, parent, x):
        Gtk.Dialog.__init__(self, x + ' settings', parent, 0)
        self.set_default_size(240, 0)

        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(6)
        self.grid.set_row_spacing(6)
        self.grid.set_property('margin', 6)

        box = self.get_content_area()
        box.add(self.grid)

        if x == 'fdkaac':
            self.fdkaac()
        if x == 'lame':
            self.lame()
        if x == 'x264':
            self.x264()
        if x == 'x265':
            self.x265()

        self.add_button('_OK', Gtk.ResponseType.OK)

        self.show_all()

    def fdkaac(self):
        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        bitrate_label = Gtk.Label('Bitrate')
        bitrate_label.set_halign(Gtk.Align.START)
        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)
        cont_label = Gtk.Label('Container')
        cont_label.set_halign(Gtk.Align.START)

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach_next_to(conf.fdkaac_mode_cbtext, mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(bitrate_label, 0, 1, 1, 1)
        self.grid.attach_next_to(conf.fdkaac_bitrate_spin, bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(quality_label, 0, 2, 1, 1)
        self.grid.attach_next_to(conf.fdkaac_quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(cont_label, 0, 3, 1, 1)
        self.grid.attach_next_to(conf.fdkaac_cont_cbtext, cont_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

        conf.fdkaac_quality_spin.set_sensitive(False)
        conf.fdkaac_mode_cbtext.connect('changed', self.on_fdkaac_mode_changed)

    def lame(self):
        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        bitrate_label = Gtk.Label('Bitrate')
        bitrate_label.set_halign(Gtk.Align.START)
        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach_next_to(conf.lame_mode_cbtext, mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(bitrate_label, 0, 1, 1, 1)
        self.grid.attach_next_to(conf.lame_bitrate_spin, bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(quality_label, 0, 2, 1, 1)
        self.grid.attach_next_to(conf.lame_quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

        conf.lame_quality_spin.set_sensitive(False)
        conf.lame_mode_cbtext.connect('changed', self.on_lame_mode_changed)

    def x264(self):
        depth_label = Gtk.Label('Depth')
        depth_label.set_halign(Gtk.Align.START)
        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)
        preset_label = Gtk.Label('Preset')
        preset_label.set_halign(Gtk.Align.START)
        tune_label = Gtk.Label('Tune')
        tune_label.set_halign(Gtk.Align.START)
        cont_label = Gtk.Label('Container')
        cont_label.set_halign(Gtk.Align.START)

        self.grid.attach(depth_label, 0, 0, 1, 1)
        self.grid.attach_next_to(conf.x264_depth_cbtext, depth_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(quality_label, 0, 1, 1, 1)
        self.grid.attach_next_to(conf.x264_quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(preset_label, 0, 2, 1, 1)
        self.grid.attach_next_to(conf.x264_preset_cbtext, preset_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(tune_label, 0, 3, 1, 1)
        self.grid.attach_next_to(conf.x264_tune_cbtext, tune_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(cont_label, 0, 4, 1, 1)
        self.grid.attach_next_to(conf.x264_cont_cbtext, cont_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def x265(self):
        depth_label = Gtk.Label('Depth')
        depth_label.set_halign(Gtk.Align.START)
        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)
        preset_label = Gtk.Label('Preset')
        preset_label.set_halign(Gtk.Align.START)
        tune_label = Gtk.Label('Tune')
        tune_label.set_halign(Gtk.Align.START)
        cont_label = Gtk.Label('Container')
        cont_label.set_halign(Gtk.Align.START)

        self.grid.attach(depth_label, 0, 0, 1, 1)
        self.grid.attach_next_to(conf.x265_depth_cbtext, depth_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(quality_label, 0, 1, 1, 1)
        self.grid.attach_next_to(conf.x265_quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(preset_label, 0, 2, 1, 1)
        self.grid.attach_next_to(conf.x265_preset_cbtext, preset_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(tune_label, 0, 3, 1, 1)
        self.grid.attach_next_to(conf.x265_tune_cbtext, tune_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(cont_label, 0, 4, 1, 1)
        self.grid.attach_next_to(conf.x265_cont_cbtext, cont_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def on_fdkaac_mode_changed(self, combo):
        m = combo.get_active_text()
        if m == 'CBR':
            conf.fdkaac_bitrate_spin.set_sensitive(True)
            conf.fdkaac_quality_spin.set_sensitive(False)
        elif m == 'VBR':
            conf.fdkaac_bitrate_spin.set_sensitive(False)
            conf.fdkaac_quality_spin.set_sensitive(True)

    def on_lame_mode_changed(self, combo):
        m = combo.get_active_text()
        if m == 'CBR' or m == 'ABR':
            conf.lame_bitrate_spin.set_sensitive(True)
            conf.lame_quality_spin.set_sensitive(False)
        elif m == 'VBR':
            conf.lame_bitrate_spin.set_sensitive(False)
            conf.lame_quality_spin.set_sensitive(True)

class VapourSynthDialog(Gtk.Dialog):

    def __init__(self, parent):
        Gtk.Dialog.__init__(self, 'VapourSynth settings', parent, 0)

        #--Notebook--#
        basic_grid = Gtk.Grid()
        basic_grid.set_column_spacing(6)
        basic_grid.set_row_spacing(6)
        basic_grid.set_property('margin', 6)
        filter_grid = Gtk.Grid()
        filter_grid.set_column_spacing(6)
        filter_grid.set_row_spacing(6)
        filter_grid.set_property('margin', 6)

        notebook = Gtk.Notebook()
        basic_label = Gtk.Label('Basic')
        notebook.append_page(basic_grid, basic_label)
        filter_label = Gtk.Label('Filters')
        notebook.append_page(filter_grid, filter_label)

        for tab in notebook.get_children():
            notebook.child_set_property(tab, 'tab-expand', True)

        box = self.get_content_area()
        box.add(notebook)

        #--Basic--#
        basic_grid.attach(conf.fps_check, 0, 0, 2, 2)
        basic_grid.attach(conf.fpsnum_spin, 2, 0, 3, 2)
        basic_grid.attach(conf.fpsden_spin, 5, 0, 3, 2)
        basic_grid.attach(conf.crop_check, 0, 2, 1, 4)
        basic_grid.attach(conf.tcrop_spin, 4, 2, 2, 2)
        basic_grid.attach(conf.bcrop_spin, 4, 4, 2, 2)
        basic_grid.attach(conf.lcrop_spin, 2, 3, 2, 2)
        basic_grid.attach(conf.rcrop_spin, 6, 3, 2, 2)
        basic_grid.attach(conf.resize_check, 0, 6, 2, 2)
        basic_grid.attach(conf.wresize_spin, 2, 6, 2, 2)
        basic_grid.attach(conf.hresize_spin, 4, 6, 2, 2)
        basic_grid.attach(conf.resize_cbtext, 6, 6, 2, 2)

        conf.fpsnum_spin.set_sensitive(False)
        conf.fpsden_spin.set_sensitive(False)
        conf.fps_check.connect('toggled', self.on_fps_toggled)
        conf.tcrop_spin.set_sensitive(False)
        conf.bcrop_spin.set_sensitive(False)
        conf.lcrop_spin.set_sensitive(False)
        conf.rcrop_spin.set_sensitive(False)
        conf.crop_check.connect('toggled', self.on_crop_toggled)
        conf.wresize_spin.set_sensitive(False)
        conf.hresize_spin.set_sensitive(False)
        conf.resize_cbtext.set_sensitive(False)
        conf.resize_check.connect('toggled', self.on_resize_toggled)

        #--Filters--#
        denoise_label = Gtk.Label()
        denoise_label.set_markup('<b>Denoise</b>')
        denoise_label.set_halign(Gtk.Align.START)
        denoise_sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        denoise_sep.set_hexpand(True)
        self.sdenoise_cfg_button = Gtk.Button()
        self.sdenoise_cfg_button.set_label('Configure')
        self.tdenoise_cfg_button = Gtk.Button()
        self.tdenoise_cfg_button.set_label('Configure')
        self.stdenoise_cfg_button = Gtk.Button()
        self.stdenoise_cfg_button.set_label('Configure')
        deband_label = Gtk.Label()
        deband_label.set_markup('<b>Deband</b>')
        deband_label.set_halign(Gtk.Align.START)
        deband_sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        deband_sep.set_hexpand(True)
        self.deband_cfg_button = Gtk.Button()
        self.deband_cfg_button.set_label('Configure')

        filter_grid.attach(denoise_label, 0, 0, 1, 1)
        filter_grid.attach_next_to(denoise_sep, denoise_label,
                                     Gtk.PositionType.RIGHT, 2, 1)
        filter_grid.attach(conf.sdenoise_check, 0, 1, 1, 1)
        filter_grid.attach_next_to(conf.sdenoise_cbtext,
                                     conf.sdenoise_check,
                                     Gtk.PositionType.RIGHT, 1, 1)
        filter_grid.attach_next_to(self.sdenoise_cfg_button,
                                     conf.sdenoise_cbtext,
                                     Gtk.PositionType.RIGHT, 1, 1)
        filter_grid.attach(conf.tdenoise_check, 0, 2, 1, 1)
        filter_grid.attach_next_to(conf.tdenoise_cbtext,
                                     conf.tdenoise_check,
                                     Gtk.PositionType.RIGHT, 1, 1)
        filter_grid.attach_next_to(self.tdenoise_cfg_button,
                                     conf.tdenoise_cbtext,
                                     Gtk.PositionType.RIGHT, 1, 1)
        filter_grid.attach(conf.stdenoise_check, 0, 3, 1, 1)
        filter_grid.attach_next_to(conf.stdenoise_cbtext,
                                     conf.stdenoise_check,
                                     Gtk.PositionType.RIGHT, 1, 1)
        filter_grid.attach_next_to(self.stdenoise_cfg_button,
                                     conf.stdenoise_cbtext,
                                     Gtk.PositionType.RIGHT, 1, 1)
        filter_grid.attach(deband_label, 0, 4, 1, 1)
        filter_grid.attach_next_to(deband_sep, deband_label,
                                     Gtk.PositionType.RIGHT, 2, 1)
        filter_grid.attach(conf.deband_check, 0, 5, 1, 1)
        filter_grid.attach_next_to(conf.deband_cbtext,
                                     conf.deband_check,
                                     Gtk.PositionType.RIGHT, 1, 1)
        filter_grid.attach_next_to(self.deband_cfg_button,
                                     conf.deband_cbtext,
                                     Gtk.PositionType.RIGHT, 1, 1)

        conf.sdenoise_cbtext.set_sensitive(False)
        self.sdenoise_cfg_button.set_sensitive(False)
        conf.sdenoise_check.connect('toggled', self.on_sdenoise_toggled)
        self.sdenoise_cfg_button.connect('clicked', self.on_conf_clicked,
                                         'spatial')
        conf.tdenoise_cbtext.set_sensitive(False)
        self.tdenoise_cfg_button.set_sensitive(False)
        conf.tdenoise_check.connect('toggled', self.on_tdenoise_toggled)
        self.tdenoise_cfg_button.connect('clicked', self.on_conf_clicked,
                                         'temporal')
        conf.stdenoise_cbtext.set_sensitive(False)
        self.stdenoise_cfg_button.set_sensitive(False)
        conf.stdenoise_check.connect('toggled', self.on_stdenoise_toggled)
        self.stdenoise_cfg_button.connect('clicked', self.on_conf_clicked,
                                          'spatio-temporal')
        conf.deband_cbtext.set_sensitive(False)
        self.deband_cfg_button.set_sensitive(False)
        conf.deband_check.connect('toggled', self.on_deband_toggled)
        self.deband_cfg_button.connect('clicked', self.on_conf_clicked,
                                       'deband')

        #--Dialogs--#
        self.rgvs_dlg = FilterDialog(self, 'RemoveGrain')
        self.rgvs_dlg.hide()
        self.tsoft_dlg = FilterDialog(self, 'TemporalSoften')
        self.tsoft_dlg.hide()
        self.fsmooth_dlg = FilterDialog(self, 'FluxSmooth')
        self.fsmooth_dlg.hide()
        self.f3kdb_dlg = FilterDialog(self, 'f3kdb')
        self.f3kdb_dlg.hide()

        self.add_button('_OK', Gtk.ResponseType.OK)

        self.show_all()

    def on_fps_toggled(self, check):
        state = check.get_active()
        conf.fpsnum_spin.set_sensitive(state)
        conf.fpsden_spin.set_sensitive(state)

    def on_crop_toggled(self, check):
        state = check.get_active()
        conf.lcrop_spin.set_sensitive(state)
        conf.rcrop_spin.set_sensitive(state)
        conf.tcrop_spin.set_sensitive(state)
        conf.bcrop_spin.set_sensitive(state)

    def on_resize_toggled(self, check):
        state = check.get_active()
        conf.wresize_spin.set_sensitive(state)
        conf.hresize_spin.set_sensitive(state)
        conf.resize_cbtext.set_sensitive(state)

    def on_sdenoise_toggled(self, check):
        state = check.get_active()
        conf.sdenoise_cbtext.set_sensitive(state)
        self.sdenoise_cfg_button.set_sensitive(state)

    def on_tdenoise_toggled(self, check):
        state = check.get_active()
        conf.tdenoise_cbtext.set_sensitive(state)
        self.tdenoise_cfg_button.set_sensitive(state)

    def on_stdenoise_toggled(self, check):
        state = check.get_active()
        conf.stdenoise_cbtext.set_sensitive(state)
        self.stdenoise_cfg_button.set_sensitive(state)

    def on_deband_toggled(self, check):
        state = check.get_active()
        conf.deband_cbtext.set_sensitive(state)
        self.deband_cfg_button.set_sensitive(state)

    def on_conf_clicked(self, button, t):
        if t == 'spatial':
            f = conf.sdenoise_cbtext.get_active_text()
        elif t == 'temporal':
            f = conf.tdenoise_cbtext.get_active_text()
        elif t == 'spatio-temporal':
            f = conf.stdenoise_cbtext.get_active_text()
        elif t == 'deband':
            f = conf.deband_cbtext.get_active_text()

        if f == 'RemoveGrain':
            self.rgvs_dlg.run()
            self.rgvs_dlg.hide()
        elif f == 'TemporalSoften':
            self.tsoft_dlg.run()
            self.tsoft_dlg.hide()
        elif f in 'FluxSmoothT':
            conf.fsmooth_st_spin.set_sensitive(False)
            self.fsmooth_dlg.run()
            self.fsmooth_dlg.hide()
        elif f == 'FluxSmoothST':
            conf.fsmooth_st_spin.set_sensitive(True)
            self.fsmooth_dlg.run()
            self.fsmooth_dlg.hide()
        elif f == 'f3kdb':
            self.f3kdb_dlg.run()
            self.f3kdb_dlg.hide()

class FilterDialog(Gtk.Dialog):

    def __init__(self, parent, f):
        Gtk.Dialog.__init__(self, f + ' settings', parent, 0)
        self.set_default_size(240, 0)

        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(6)
        self.grid.set_row_spacing(6)
        self.grid.set_property('margin', 6)

        box = self.get_content_area()
        box.add(self.grid)

        if f == 'RemoveGrain':
            self.rgvs()
        if f == 'TemporalSoften':
            self.tsoft()
        if f == 'FluxSmooth':
            self.fsmooth()
        if f == 'f3kdb':
            self.f3kdb()

        self.add_button('_OK', Gtk.ResponseType.OK)

        self.show_all()

    def rgvs(self):
        adv_label = Gtk.Label('Advanced')
        adv_label.set_halign(Gtk.Align.START)
        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        modeu_label = Gtk.Label('U Mode')
        modeu_label.set_halign(Gtk.Align.START)
        modev_label = Gtk.Label('V Mode')
        modev_label.set_halign(Gtk.Align.START)

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach(conf.rgvs_mode_spin, 1, 0, 1, 1)
        self.grid.attach(adv_label, 0, 1, 1, 1)
        self.grid.attach(conf.rgvs_adv_check, 1, 1, 1, 1)
        self.grid.attach(modeu_label, 0, 2, 1, 1)
        self.grid.attach(conf.rgvs_modeu_spin, 1, 2, 1, 1)
        self.grid.attach(modev_label, 0, 3, 1, 1)
        self.grid.attach(conf.rgvs_modev_spin, 1, 3, 1, 1)

        conf.rgvs_modeu_spin.set_sensitive(False)
        conf.rgvs_modev_spin.set_sensitive(False)
        conf.rgvs_adv_check.connect('toggled', self.on_rgvs_adv_toggled)

    def on_rgvs_adv_toggled(self, check):
        state = conf.rgvs_adv_check.get_active()
        conf.rgvs_modeu_spin.set_sensitive(state)
        conf.rgvs_modev_spin.set_sensitive(state)

    def tsoft(self):
        rad_label = Gtk.Label('Radius')
        rad_label.set_halign(Gtk.Align.START)
        lt_label = Gtk.Label('Luma Threshold')
        lt_label.set_halign(Gtk.Align.START)
        ct_label = Gtk.Label('Chroma Threshold')
        ct_label.set_halign(Gtk.Align.START)
        sc_label = Gtk.Label('Scene Change')
        sc_label.set_halign(Gtk.Align.START)

        self.grid.attach(rad_label, 0, 0, 1, 1)
        self.grid.attach(conf.tsoft_rad_spin, 1, 0, 1, 1)
        self.grid.attach(lt_label, 0, 1, 1, 1)
        self.grid.attach(conf.tsoft_lt_spin, 1, 1, 1, 1)
        self.grid.attach(ct_label, 0, 2, 1, 1)
        self.grid.attach(conf.tsoft_ct_spin, 1, 2, 1, 1)
        self.grid.attach(sc_label, 0, 3, 1, 1)
        self.grid.attach(conf.tsoft_sc_spin, 1, 3, 1, 1)

    def fsmooth(self):
        st_label = Gtk.Label('Spatial Threshold')
        st_label.set_halign(Gtk.Align.START)
        tt_label = Gtk.Label('Temporal Threshold')
        tt_label.set_halign(Gtk.Align.START)
        planes_label = Gtk.Label('Planes')
        planes_label.set_halign(Gtk.Align.START)

        self.grid.attach(st_label, 0, 0, 1, 1)
        self.grid.attach(conf.fsmooth_st_spin, 1, 0, 3, 1)
        self.grid.attach(tt_label, 0, 1, 1, 1)
        self.grid.attach(conf.fsmooth_tt_spin, 1, 1, 3, 1)
        self.grid.attach(planes_label, 0, 2, 1, 1)
        self.grid.attach(conf.fsmooth_y_check, 1, 2, 1, 1)
        self.grid.attach(conf.fsmooth_u_check, 2, 2, 1, 1)
        self.grid.attach(conf.fsmooth_v_check, 3, 2, 1, 1)

    def f3kdb(self):
        preset_label = Gtk.Label('Preset')
        preset_label.set_halign(Gtk.Align.START)
        plane_label = Gtk.Label('Plane')
        plane_label.set_halign(Gtk.Align.START)
        grain_label = Gtk.Label('Grain')
        grain_label.set_halign(Gtk.Align.START)
        depth_label = Gtk.Label('Output Depth')
        depth_label.set_halign(Gtk.Align.START)

        self.grid.attach(preset_label, 0, 0, 1, 1)
        self.grid.attach(conf.f3kdb_preset_cbtext, 1, 0, 1, 1)
        self.grid.attach(plane_label, 0, 1, 1, 1)
        self.grid.attach(conf.f3kdb_plane_cbtext, 1, 1, 1, 1)
        self.grid.attach(grain_label, 0, 2, 1, 1)
        self.grid.attach(conf.f3kdb_grain_check, 1, 2, 1, 1)
        self.grid.attach(depth_label, 0, 3, 1, 1)
        self.grid.attach(conf.f3kdb_depth_spin, 1, 3, 1, 1)

class AboutDialog(Gtk.AboutDialog):

    def __init__(self, parent):
        Gtk.Dialog.__init__(self, parent)
        self.set_property('program-name', 'pyanimenc')
        self.set_property('version', VERSION)
        self.set_property('comments', 'Python Transcoding Tools')
        self.set_property('copyright', 'Copyright © 2014-2015 Maxime Gauduin')
        self.set_property('license-type', Gtk.License.GPL_3_0)
        self.set_property('website', 'https://github.com/alucryd/pyanimenc')

conf = Config()

win = MainWindow()
win.connect('delete-event', Gtk.main_quit)

sccr_win = ScriptCreatorWindow()
ched_win = ChapterEditorWindow()

vs_dlg = VapourSynthDialog(win)
vs_dlg.hide()

win.show_all()

Gtk.main()

# vim: ts=4 sw=4 et:
