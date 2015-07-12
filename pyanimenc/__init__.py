#!/usr/bin/env python3

import os
import re
import subprocess
import yaml
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from gi.repository import Gio, GLib, GObject, Gtk
from pyanimenc.helpers import Chapters, Encode, MatroskaOps
from threading import Lock

VERSION = '0.1b1'
AUTHOR = 'Maxime Gauduin <alucryd@gmail.com>'

VENCS = OrderedDict()
VENCS['AVC (x264)'] = ['x264', 8]
VENCS['AVC (x264, High10)'] = ['x264', 10]
VENCS['HEVC (x265)'] = ['x265', 8]
VENCS['HEVC (x265, Main10)'] = ['x265', 10]
VENCS['HEVC (x265, Main12)'] = ['x265', 12]

VTYPES = {'V_MPEG4/ISO/AVC': 'h264',
          'V_MPEGH/ISO/HEVC': 'h265',
          'V_MS/VFW/FOURCC': 'xvid'}

ADECS = OrderedDict()
ADECS['DTS-HD (FFmpeg, libdcadec)'] = ['ffmpeg', 'libdcadec']

AENCS = OrderedDict()
AENCS['AAC (FFmpeg, libfaac)'] = ['ffmpeg', 'libfaac']
AENCS['AAC (faac)'] = ['faac', '']
AENCS['AAC (FFmpeg, libfdk_aac)'] = ['ffmpeg', 'libfdk-aac']
AENCS['AAC (fdkaac)'] = ['fdkaac', '']
AENCS['FLAC (FFmpeg)'] = ['ffmpeg', 'native-flac']
AENCS['FLAC (flac)'] = ['flac', '']
AENCS['MP3 (FFmpeg, libmp3lame)'] = ['ffmpeg', 'libmp3lame']
AENCS['MP3 (lame)'] = ['lame', '']
AENCS['Opus (FFmpeg, libopus)'] = ['ffmpeg', 'libopus']
AENCS['Opus (opusenc)'] = ['opusenc', '']
AENCS['Vorbis (FFmpeg, libvorbis)'] = ['ffmpeg', 'libvorbis']
AENCS['Vorbis (oggenc)'] = ['oggenc', '']

ATYPES = {'A_AAC': 'aac',
          'A_AAC/MPEG2/LC/SBR': 'aac',
          'A_AC3': 'ac3',
          'A_DTS': 'dts',
          'A_FLAC': 'flac',
          'A_MP3': 'mp3',
          'A_TRUEHD': 'thd',
          'A_VORBIS': 'ogg',
          'A_WAVPACK4': 'wv'}

STYPES = {'S_HDMV/PGS': 'sup',
          'S_TEXT/ASS': 'ass',
          'S_TEXT/SSA': 'ass',
          'S_TEXT/UTF8': 'srt',
          'S_VOBSUB': 'sub'}

SOURCE_FLTS = OrderedDict()
SOURCE_FLTS['FFMpegSource'] = None
SOURCE_FLTS['LibavSMASHSource'] = None
SOURCE_FLTS['LWLibavSource'] = None

CROP_FLTS = OrderedDict()
CROP_FLTS['CropAbs'] = None
CROP_FLTS['CropRel'] = None

RESIZE_FLTS = OrderedDict()
RESIZE_FLTS['Bilinear'] = None
RESIZE_FLTS['Bicubic'] = None
RESIZE_FLTS['Gauss'] = None
RESIZE_FLTS['Lanczos'] = None
RESIZE_FLTS['Point'] = None
RESIZE_FLTS['Sinc'] = None
RESIZE_FLTS['Spline'] = None

DENOISE_FLTS = OrderedDict()
DENOISE_FLTS['FluxSmoothT'] = None
DENOISE_FLTS['FluxSmoothST'] = None
DENOISE_FLTS['RemoveGrain'] = None
DENOISE_FLTS['TemporalSoften'] = None

DEBAND_FLTS = OrderedDict()
DEBAND_FLTS['f3kdb'] = None

MISC_FLTS = OrderedDict()
MISC_FLTS['Trim'] = None

FILTERS = OrderedDict()
FILTERS['Source'] = SOURCE_FLTS
FILTERS['Crop'] = CROP_FLTS
FILTERS['Resize'] = RESIZE_FLTS
FILTERS['Denoise'] = DENOISE_FLTS
FILTERS['Deband'] = DEBAND_FLTS
FILTERS['Misc'] = MISC_FLTS

# File Filters
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
        for key in VENCS:
            venc = VENCS[key][0]
            vdepth = VENCS[key][1]
            if not self._find_enc(venc, vdepth):
                venc = '{}-{}bit'.format(venc, vdepth)
                VENCS[key][0] = venc
                if not self._find_enc(venc, vdepth):
                    VENCS.pop(key)

        for key in AENCS:
            aenc = AENCS[key][0]
            alib = AENCS[key][1]
            if not self._find_enc(aenc, alib):
                AENCS.pop(key)

        self.filters = [['Source', 'FFMpegSource', OrderedDict()]]

        self.x264 = {'quality': 18,
                     'preset': 'medium',
                     'tune': 'none',
                     'container': '264',
                     'arguments': ''}

        self.x265 = {'quality': 18,
                     'preset': 'medium',
                     'tune': 'none',
                     'container': '265',
                     'arguments': ''}

        self.faac = {'mode': 'VBR',
                     'bitrate': 128,
                     'quality': 100,
                     'container': 'm4a'}

        self.fdkaac = {'mode': 'VBR',
                       'bitrate': 128,
                       'quality': 4,
                       'container': 'm4a'}

        self.flac = {'compression': 8,
                     'container': 'flac'}

        self.mp3 = {'mode': 'VBR',
                    'bitrate': 192,
                    'quality': 2,
                    'container': 'mp3'}

        self.opus = {'mode': 'VBR',
                     'bitrate': 128,
                     'container': 'opus'}

        self.vorbis = {'mode': 'VBR',
                       'bitrate': 160,
                       'quality': 5,
                       'container': 'ogg'}

    def _find_enc(self, x, y=''):
        path = os.environ['PATH'].split(':')
        for p in path:
            if os.path.isfile('/'.join([p, x])):
                if x.startswith('x264') and not self._find_x264(x, y):
                    return False
                elif x.startswith('x265') and not self._find_x265(x, y):
                    return False
                elif x == 'ffmpeg' and y and not self._find_ffmpeg(y):
                    return False
                else:
                    return True
        return False

    def _find_ffmpeg(self, y):
        proc = subprocess.Popen('ffmpeg -buildconf',
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL,
                                universal_newlines=True)
        line = proc.stdout.readline()
        while line:
            if '--enable-' + y in line or y.startswith('native'):
                return True
            line = proc.stdout.readline()
        return False

    def _find_x264(self, x, y):
        cmd = [x, '--version']
        cmd = ' '.join(cmd)
        proc = subprocess.Popen(cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        line = proc.stdout.readline()
        while line:
            if '--bit-depth=' + str(y) in line:
                return True
            line = proc.stdout.readline()
        return False

    def _find_x265(self, x, y):
        cmd = [x, '--output-depth', str(y), '--version']
        cmd = ' '.join(cmd)
        proc = subprocess.Popen(cmd,
                                shell=True,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
        line = proc.stderr.readline()
        while line:
            if str(y) + 'bit' in line:
                return True
            line = proc.stderr.readline()
        return False

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

        #--Worker--#
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.idle = True
        self.lock = Lock()
        self.lock.acquire()

        #--Queue--#
        self.queue_tstore = Gtk.TreeStore(GObject.TYPE_PYOBJECT, str, str, str)
        # Do one encoding task at a time

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
        k = self.venc_cbtext.get_active_text()
        x = VENCS[k]
        i = self.vsrc_fcbutton.get_filename()
        wd, f = os.path.split(i)
        if not os.path.isdir(wd + '/out'):
            os.mkdir(wd + '/out')
        o = wd + '/out/' + os.path.splitext(f)[0]
        if x[0].startswith('x264'):
            q = conf.x264['quality']
            p = conf.x264['preset']
            t = conf.x264['tune']
            c = conf.x264['container']
            a = conf.x264['arguments']
            future = self.worker.submit(self._x264, i, x[0], o, q, p, t, c, a)
        elif x[0].startswith('x265'):
            q = conf.x265['quality']
            p = conf.x265['preset']
            t = conf.x265['tune']
            c = conf.x265['container']
            a = conf.x265['arguments']
            future = self.worker.submit(self._x265, i, x[0], x[1], o, q, p, t,
                                        c, a)
        self.queue_tstore.append(None, [future, f, x[0], 'Waiting'])
        self.worker.submit(self._update_queue)

    def on_asrc_file_set(self, button):
        self.aqueue_button.set_sensitive(True)

    def on_aqueue_clicked(self, button):
        self.worker.submit(self._wait)
        k = self.aenc_cbtext.get_active_text()
        x = AENCS[k]
        i = self.asrc_fcbutton.get_filename()
        wd, f = os.path.split(i)
        if not os.path.isdir(wd + '/out'):
            os.mkdir(wd + '/out')
        o = wd + '/out/' + os.path.splitext(f)[0]
        if x[0] == 'faac' or x[1] == 'libfaac':
            m = conf.faac['mode']
            b = conf.faac['bitrate']
            q = conf.faac['quality']
            c = conf.faac['container']
            if x[0] == 'faac':
                future = self.worker.submit(self._faac, i, o, m, b, q, c)
            elif x[0] == 'ffmpeg':
                future = self.worker.submit(self._libfaac, i, o, m, b, q, c)
        elif x[0] == 'fdkaac' or x[1] == 'libfdk-aac':
            m = conf.fdkaac['mode']
            b = conf.fdkaac['bitrate']
            q = conf.fdkaac['quality']
            c = conf.fdkaac['container']
            if x[0] == 'fdkaac':
                future = self.worker.submit(self._fdkaac, i, o, m, b, q, c)
            elif x[0] == 'ffmpeg':
                future = self.worker.submit(self._libfdk_aac, i, o, m, b, q, c)
        elif x[0] == 'flac' or x[1] == 'native-flac':
            cp = conf.flac['compression']
            c = conf.flac['container']
            if x[0] == 'flac':
                future = self.worker.submit(self._flac, i, o, cp, c)
            elif x[0] == 'ffmpeg':
                future = self.worker.submit(self._native_flac, i, o, cp, c)
        elif x[0] == 'lame' or x[1] == 'libmp3lame':
            m = conf.mp3['mode']
            b = conf.mp3['bitrate']
            q = conf.mp3['quality']
            c = conf.mp3['container']
            if x[0] == 'lame':
                future = self.worker.submit(self._lame, i, o, m, b, q, c)
            elif x[0] == 'ffmpeg':
                future = self.worker.submit(self._libmp3lame, i, o, m, b, q, c)
        elif x[0] == 'opusenc' or x[1] == 'libopus':
            m = conf.opus['mode']
            b = conf.opus['bitrate']
            c = conf.opus['container']
            if x[0] == 'opusenc':
                future = self.worker.submit(self._opusenc, i, o, m, b, c)
            elif x[0] == 'ffmpeg':
                future = self.worker.submit(self._libopus, i, o, m, b, c)
        elif x[0] == 'oggenc' or x[1] == 'libvorbis':
            m = conf.vorbis['mode']
            b = conf.vorbis['bitrate']
            q = conf.vorbis['quality']
            c = conf.vorbis['container']
            if x[0] == 'oggenc':
                future = self.worker.submit(self._oggenc, i, o, m, b, q, c)
            elif x[0] == 'ffmpeg':
                future = self.worker.submit(self._libvorbis, i, o, m, b, q, c)
        self.queue_tstore.append(None, [future, f, x[0], 'Waiting'])
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

                vpy = wd + '/out/' + basename + '.vpy'

                self.worker.submit(self._vpy, source, vpy)

                # Encode video
                k = self.auto_venc_cbtext.get_active_text()
                x = VENCS[k]
                o = vtrack[1]
                if x[0].startswith('x264'):
                    q = conf.x264['quality']
                    p = conf.x264['preset']
                    t = conf.x264['tune']
                    c = conf.x264['container']
                    a = conf.x264['arguments']
                    vtrack[2] = c

                    future = self.worker.submit(self._x264, vpy, x[0], o, q, p,
                                                t, c, a)
                if x[0].startswith('x265'):
                    q = conf.x265['quality']
                    p = conf.x265['preset']
                    t = conf.x265['tune']
                    c = conf.x265['container']
                    a = conf.x265['arguments']
                    vtrack[2] = c

                    future = self.worker.submit(self._x265, vpy, x[0], x[1], o,
                                                q, p, t, c, a)

                self.queue_tstore.append(job, [future, '', x[0], 'Waiting'])

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
                    k = self.auto_aenc_cbtext.get_active_text()
                    x = AENCS[k]
                    i = track[1] + '.' + track[2]
                    o = track[1]
                    if x[0] == 'faac' or x[1] == 'libfaac':
                        m = conf.faac['mode']
                        b = conf.faac['bitrate']
                        q = conf.faac['quality']
                        c = conf.faac['container']
                        #track[2] = c
                        if x[0] == 'faac':
                            future = self.worker.submit(self._faac, i, o, m, b,
                                                        q, c)
                        elif x[0] == 'ffmpeg':
                            future = self.worker.submit(self._libfaac, i, o, m,
                                                        b, q, c)
                    elif x[0] == 'fdkaac' or x[1] == 'libfdk-aac':
                        m = conf.fdkaac['mode']
                        b = conf.fdkaac['bitrate']
                        q = conf.fdkaac['quality']
                        c = conf.fdkaac['container']
                        #track[2] = c
                        if x[0] == 'fdkaac':
                            future = self.worker.submit(self._fdkaac, i, o,
                                                        m, b, q, c)
                        elif x[0] == 'ffmpeg':
                            future = self.worker.submit(self._libfdk_aac,
                                                        i, o, m, b, q, c)
                    elif x[0] == 'flac' or x[1] == 'native-flac':
                        cp = conf.flac['compression']
                        c = conf.flac['container']
                        #track[2] = c
                        if x[0] == 'flac':
                            future = self.worker.submit(self._flac, i, o,
                                                        cp, c)
                        elif x[0] == 'ffmpeg':
                            future = self.worker.submit(self._native_flac,
                                                        i, o, cp, c)
                    elif x[0] == 'lame' or x[1] == 'libmp3lame':
                        m = conf.mp3['mode']
                        b = conf.mp3['bitrate']
                        q = conf.mp3['quality']
                        c = conf.mp3['container']
                        #track[2] = c
                        if x[0] == 'lame':
                            future = self.worker.submit(self._lame, i, o,
                                                        m, b, q, c)
                        elif x[0] == 'ffmpeg':
                            future = self.worker.submit(self._libmp3lame,
                                                        i, o, m, b, q, c)
                    elif x[0] == 'opusenc' or x[1] == 'libopus':
                        m = conf.opus['mode']
                        b = conf.opus['bitrate']
                        c = conf.opus['container']
                        #track[2] = c
                        if x[0] == 'opusenc':
                            future = self.worker.submit(self._opus, i, o,
                                                        m, b, c)
                        elif x[0] == 'ffmpeg':
                            future = self.worker.submit(self._libopus, i,
                                                        o, m, b, c)
                    elif x[0] == 'oggenc' or x[1] == 'libvorbis':
                        m = conf.vorbis['mode']
                        b = conf.vorbis['bitrate']
                        q = conf.vorbis['quality']
                        c = conf.vorbis['container']
                        #track[2] = c
                        if x[0] == 'oggenc':
                            future = self.worker.submit(self._oggenc, i, o,
                                                        m, b, q, c)
                        elif x[0] == 'ffmpeg':
                            future = self.worker.submit(self._libvorbis, i,
                                                        o, m, b, q, c)

                    self.queue_tstore.append(job, [future, '', x[0],
                                             'Waiting'])

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
                enc = self.venc_cbtext.get_active_text()
                enc = VENCS[enc]
            elif t == 'audio':
                enc = self.aenc_cbtext.get_active_text()
                enc = AENCS[enc]
        elif m == 'auto':
            if t == 'video':
                enc = self.auto_venc_cbtext.get_active_text()
                enc = VENCS[enc]
            elif t == 'audio':
                enc = self.auto_aenc_cbtext.get_active_text()
                enc = AENCS[enc]

        dlg = EncoderDialog(self, enc)
        dlg.run()
        dlg.destroy()

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
                k = self.auto_aenc_cbtext.get_active_text()
                x = AENCS[k]
                if x[0] == 'faac' or x[1] == 'libfaac':
                    c = conf.faac['container']
                    track[2] = c
                elif x[0] == 'fdkaac' or x[1] == 'libfdk-aac':
                    c = conf.fdkaac['container']
                    track[2] = c
                elif x[0] == 'flac' or x[1] == 'native-flac':
                    c = conf.flac['container']
                    track[2] = c
                elif x[0] == 'lame' or x[1] == 'libmp3lame':
                    c = conf.mp3['container']
                    track[2] = c
                elif x[0] == 'opusenc' or x[1] == 'libopus':
                    c = conf.opus['container']
                    track[2] = c
                elif x[0] == 'oggenc' or x[1] == 'libvorbis':
                    c = conf.vorbis['container']
                    track[2] = c

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

    def _vpy(self, source, destination):
        print('Create VapourSynth script...')
        v = Encode(source).vpy(conf.filters)

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
                dur = int(line.split(' ')[1])
        return dur

    def _x264(self, i, x, o, q, p, t, c, a):
        print('Encode video...')
        self._update_queue()
        dur = self._info(i)
        cmd = Encode(i).x264(x, o, q, p, t, c, a)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._video_progress(dur)

    def _x265(self, i, x, o, d, q, p, t, c, a):
        print('Encode video...')
        self._update_queue()
        dur = self._info(i)
        cmd = Encode(i).x265(x, o, d, q, p, t, c, a)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._video_progress(dur)

    def _faac(self, i, o, m, b, q, c):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(i).faac(o, m, b, q, c)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libfdk_aac(self, i, o, m, b, q, c):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(i).ffmpeg_libfaac(o, m, b, q, c)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _fdkaac(self, i, o, m, b, q, c):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(i).fdkaac(o, m, b, q, c)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libfdk_aac(self, i, o, m, b, q, c):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(i).ffmpeg_libfdk_aac(o, m, b, q, c)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _flac(self, i, o, cp, c):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(i).flac(o, cp, c)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _native_flac(self, i, o, cp, c):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(i).ffmpeg_flac(o, cp, c)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _lame(self, i, o, m, b, q, c):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(i).lame(o, m, b, q, c)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libmp3lame(self, i, o, m, b, q, c):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(i).ffmpeg_libmp3lame(o, m, b, q, c)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _opusenc(self, i, o, m, b, c):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(i).opusenc(o, m, b, c)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libopus(self, i, o, m, b, c):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(i).ffmpeg_libopus(o, m, b, c)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _oggenc(self, i, o, m, b, q, c):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(i).oggenc(o, m, b, q, c)
        print(cmd)
        self.proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        self._audio_progress()

    def _libvorbis(self, i, o, m, b, q, c):
        print('Encode audio...')
        self._update_queue()
        cmd = Encode(i).ffmpeg_libvorbis(o, m, b, q, c)
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
        s = Encode(self.source).vpy(conf.filters)
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
        if x[0] == 'ffmpeg':
            n = x[1]
        else:
            n = x[0]

        Gtk.Dialog.__init__(self, n + ' settings', parent, 0)
        self.set_default_size(240, 0)

        button = self.add_button('_OK', Gtk.ResponseType.OK)

        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(6)
        self.grid.set_row_spacing(6)
        self.grid.set_property('margin', 6)

        box = self.get_content_area()
        box.add(self.grid)

        if n.startswith('x264'):
            self._x264()
            button.connect('clicked', self._update_x264)
        if n.startswith('x265'):
            self._x265()
            button.connect('clicked', self._update_x265)
        if n == 'fdkaac' or n == 'libfdk-aac':
            self._fdkaac()
            button.connect('clicked', self._update_fdkaac)
        if n == 'faac' or n == 'libfaac':
            self._faac()
            button.connect('clicked', self._update_faac)
        if n == 'flac' or n == 'native-flac':
            self._flac()
            button.connect('clicked', self._update_flac)
        if n == 'lame' or n == 'libmp3lame':
            self._mp3()
            button.connect('clicked', self._update_mp3)
        if n == 'opusenc'or n == 'libopus':
            self._opus()
            button.connect('clicked', self._update_opus)
        if n == 'oggenc' or n == 'libvorbis':
            self._vorbis()
            button.connect('clicked', self._update_vorbis)

        self.show_all()

    def _x264(self):
        quality = Gtk.Adjustment(18, 1, 51, 1, 10)
        presets = ['none',
                   'ultrafast',
                   'superfast',
                   'veryfast',
                   'faster',
                   'fast',
                   'medium',
                   'slow',
                   'slower',
                   'veryslow',
                   'placebo']
        tunes = ['none',
                 'film',
                 'animation',
                 'grain',
                 'stillimage',
                 'psnr',
                 'ssim',
                 'fastdecode',
                 'zerolatency']
        conts = ['264',
                 'flv',
                 'mp4',
                 'mkv']

        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)
        preset_label = Gtk.Label('Preset')
        preset_label.set_halign(Gtk.Align.START)
        tune_label = Gtk.Label('Tune')
        tune_label.set_halign(Gtk.Align.START)
        cont_label = Gtk.Label('Container')
        cont_label.set_halign(Gtk.Align.START)
        arg_label = Gtk.Label('Custom arguments')
        arg_label.set_halign(Gtk.Align.CENTER)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(quality)

        self.preset_cbtext = Gtk.ComboBoxText()
        self.preset_cbtext.set_property('hexpand', True)
        for p in presets:
            self.preset_cbtext.append_text(p)

        self.tune_cbtext = Gtk.ComboBoxText()
        self.tune_cbtext.set_property('hexpand', True)
        for t in tunes:
            self.tune_cbtext.append_text(t)

        self.cont_cbtext = Gtk.ComboBoxText()
        self.cont_cbtext.set_property('hexpand', True)
        for c in conts:
            self.cont_cbtext.append_text(c)

        self.arg_entry = Gtk.Entry()
        self.arg_entry.set_property('hexpand', True)

        self.quality_spin.set_value(conf.x264['quality'])
        i = presets.index(conf.x264['preset'])
        self.preset_cbtext.set_active(i)
        j = tunes.index(conf.x264['tune'])
        self.tune_cbtext.set_active(j)
        k = conts.index(conf.x264['container'])
        self.cont_cbtext.set_active(k)
        self.arg_entry.set_text(conf.x264['arguments'])

        self.grid.attach(quality_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(preset_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.preset_cbtext, preset_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(tune_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.tune_cbtext, tune_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(cont_label, 0, 3, 1, 1)
        self.grid.attach_next_to(self.cont_cbtext, cont_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(arg_label, 0, 4, 2, 1)
        self.grid.attach(self.arg_entry, 0, 5, 2, 1)

    def _update_x264(self, button):
        q = self.quality_spin.get_value_as_int()
        p = self.preset_cbtext.get_active_text()
        t = self.tune_cbtext.get_active_text()
        c = self.cont_cbtext.get_active_text()
        a = self.arg_entry.get_text()

        conf.x264['quality'] = q
        conf.x264['preset'] = p
        conf.x264['tune'] = t
        conf.x264['container'] = c
        conf.x264['arguments'] = a

    def _x265(self):
        quality = Gtk.Adjustment(18, 1, 51, 1, 10)
        presets = ['none',
                   'ultrafast',
                   'superfast',
                   'veryfast',
                   'faster',
                   'fast',
                   'medium',
                   'slow',
                   'slower',
                   'veryslow',
                   'placebo']
        tunes = ['none',
                 'psnr',
                 'ssim',
                 'fastdecode',
                 'zerolatency']
        conts = ['265']

        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)
        preset_label = Gtk.Label('Preset')
        preset_label.set_halign(Gtk.Align.START)
        tune_label = Gtk.Label('Tune')
        tune_label.set_halign(Gtk.Align.START)
        cont_label = Gtk.Label('Container')
        cont_label.set_halign(Gtk.Align.START)
        arg_label = Gtk.Label('Custom arguments')
        arg_label.set_halign(Gtk.Align.CENTER)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(quality)

        self.preset_cbtext = Gtk.ComboBoxText()
        self.preset_cbtext.set_property('hexpand', True)
        for p in presets:
            self.preset_cbtext.append_text(p)

        self.tune_cbtext = Gtk.ComboBoxText()
        self.tune_cbtext.set_property('hexpand', True)
        for t in tunes:
            self.tune_cbtext.append_text(t)

        self.cont_cbtext = Gtk.ComboBoxText()
        self.cont_cbtext.set_property('hexpand', True)
        for c in conts:
            self.cont_cbtext.append_text(c)

        self.arg_entry = Gtk.Entry()
        self.arg_entry.set_property('hexpand', True)

        self.quality_spin.set_value(conf.x265['quality'])
        i = presets.index(conf.x265['preset'])
        self.preset_cbtext.set_active(i)
        j = tunes.index(conf.x265['tune'])
        self.tune_cbtext.set_active(j)
        k = conts.index(conf.x265['container'])
        self.cont_cbtext.set_active(k)
        self.arg_entry.set_text(conf.x265['arguments'])

        self.grid.attach(quality_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(preset_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.preset_cbtext, preset_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(tune_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.tune_cbtext, tune_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(cont_label, 0, 3, 1, 1)
        self.grid.attach_next_to(self.cont_cbtext, cont_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(arg_label, 0, 4, 2, 1)
        self.grid.attach(self.arg_entry, 0, 5, 2, 1)

    def _update_x265(self, button):
        q = self.quality_spin.get_value_as_int()
        p = self.preset_cbtext.get_active_text()
        t = self.tune_cbtext.get_active_text()
        c = self.cont_cbtext.get_active_text()
        a = self.arg_entry.get_text()

        conf.x265['quality'] = q
        conf.x265['preset'] = p
        conf.x265['tune'] = t
        conf.x265['container'] = c
        conf.x265['arguments'] = a

    def _faac(self):
        modes = ['ABR', 'VBR']
        bitrate = Gtk.Adjustment(128, 0, 320, 1, 10)
        quality = Gtk.Adjustment(100, 10, 500, 10, 100)
        conts = ['aac', 'm4a']

        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        bitrate_label = Gtk.Label('Bitrate')
        bitrate_label.set_halign(Gtk.Align.START)
        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)
        cont_label = Gtk.Label('Container')
        cont_label.set_halign(Gtk.Align.START)

        self.mode_cbtext = Gtk.ComboBoxText()
        self.mode_cbtext.set_property('hexpand', True)
        for m in modes:
            self.mode_cbtext.append_text(m)
        self.mode_cbtext.connect('changed', self.on_mode_changed)

        self.bitrate_spin = Gtk.SpinButton()
        self.bitrate_spin.set_property('hexpand', True)
        self.bitrate_spin.set_numeric(True)
        self.bitrate_spin.set_adjustment(bitrate)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(quality)

        self.cont_cbtext = Gtk.ComboBoxText()
        self.cont_cbtext.set_property('hexpand', True)
        for c in conts:
            self.cont_cbtext.append_text(c)

        i = modes.index(conf.faac['mode'])
        self.mode_cbtext.set_active(i)
        self.bitrate_spin.set_value(conf.faac['bitrate'])
        self.quality_spin.set_value(conf.faac['quality'])
        j = conts.index(conf.faac['container'])
        self.cont_cbtext.set_active(j)

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(bitrate_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(quality_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(cont_label, 0, 3, 1, 1)
        self.grid.attach_next_to(self.cont_cbtext, cont_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def _update_faac(self, button):
        m = self.mode_cbtext.get_active_text()
        b = self.bitrate_spin.get_value_as_int()
        q = self.quality_spin.get_value_as_int()
        c = self.cont_cbtext.get_active_text()

        conf.faac['mode'] = m
        conf.faac['bitrate'] = b
        conf.faac['quality'] = q
        conf.faac['container'] = c

    def _fdkaac(self):
        modes = ['CBR', 'VBR']
        bitrate = Gtk.Adjustment(128, 0, 320, 1, 10)
        quality = Gtk.Adjustment(4, 1, 5, 1, 10)
        conts = ['aac', 'm4a']

        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        bitrate_label = Gtk.Label('Bitrate')
        bitrate_label.set_halign(Gtk.Align.START)
        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)
        cont_label = Gtk.Label('Container')
        cont_label.set_halign(Gtk.Align.START)

        self.mode_cbtext = Gtk.ComboBoxText()
        self.mode_cbtext.set_property('hexpand', True)
        for m in modes:
            self.mode_cbtext.append_text(m)
        self.mode_cbtext.connect('changed', self.on_mode_changed)

        self.bitrate_spin = Gtk.SpinButton()
        self.bitrate_spin.set_property('hexpand', True)
        self.bitrate_spin.set_numeric(True)
        self.bitrate_spin.set_adjustment(bitrate)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(quality)

        self.cont_cbtext = Gtk.ComboBoxText()
        self.cont_cbtext.set_property('hexpand', True)
        for c in conts:
            self.cont_cbtext.append_text(c)

        i = modes.index(conf.fdkaac['mode'])
        self.mode_cbtext.set_active(i)
        self.bitrate_spin.set_value(conf.fdkaac['bitrate'])
        self.quality_spin.set_value(conf.fdkaac['quality'])
        j = conts.index(conf.fdkaac['container'])
        self.cont_cbtext.set_active(j)

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(bitrate_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(quality_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(cont_label, 0, 3, 1, 1)
        self.grid.attach_next_to(self.cont_cbtext, cont_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def _update_fdkaac(self, button):
        m = self.mode_cbtext.get_active_text()
        b = self.bitrate_spin.get_value_as_int()
        q = self.quality_spin.get_value_as_int()
        c = self.cont_cbtext.get_active_text()

        conf.fdkaac['mode'] = m
        conf.fdkaac['bitrate'] = b
        conf.fdkaac['quality'] = q
        conf.fdkaac['container'] = c

    def _flac(self):
        compression = Gtk.Adjustment(8, 0, 8, 1, 10)

        compression_label = Gtk.Label('Compression')
        compression_label.set_halign(Gtk.Align.START)

        self.compression_spin = Gtk.SpinButton()
        self.compression_spin.set_property('hexpand', True)
        self.compression_spin.set_numeric(True)
        self.compression_spin.set_adjustment(compression)

        self.compression_spin.set_value(conf.flac['compression'])

        self.grid.attach(compression_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.compression_spin, compression_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def _update_flac(self, button):
        c = self.compression_spin.get_value_as_int()

        conf.flac['compression'] = c

    def _mp3(self):
        modes = ['CBR', 'ABR', 'VBR']
        bitrate = Gtk.Adjustment(320, 0, 320, 1, 10)
        quality = Gtk.Adjustment(4, 0, 9, 1, 10)

        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        bitrate_label = Gtk.Label('Bitrate')
        bitrate_label.set_halign(Gtk.Align.START)
        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)

        self.mode_cbtext = Gtk.ComboBoxText()
        self.mode_cbtext.set_property('hexpand', True)
        for m in modes:
            self.mode_cbtext.append_text(m)
        self.mode_cbtext.connect('changed', self.on_mode_changed)

        self.bitrate_spin = Gtk.SpinButton()
        self.bitrate_spin.set_property('hexpand', True)
        self.bitrate_spin.set_numeric(True)
        self.bitrate_spin.set_adjustment(bitrate)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(quality)

        i = modes.index(conf.mp3['mode'])
        self.mode_cbtext.set_active(i)
        self.bitrate_spin.set_value(conf.mp3['bitrate'])
        self.quality_spin.set_value(conf.mp3['quality'])

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(bitrate_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(quality_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def _update_mp3(self, button):
        m = self.mode_cbtext.get_active_text()
        b = self.bitrate_spin.get_value_as_int()
        q = self.quality_spin.get_value_as_int()

        conf.mp3['mode'] = m
        conf.mp3['bitrate'] = b
        conf.mp3['quality'] = q

    def _opus(self):
        modes = ['CBR', 'ABR', 'VBR']
        bitrate = Gtk.Adjustment(128, 0, 510, 1, 10)

        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        bitrate_label = Gtk.Label('Bitrate')
        bitrate_label.set_halign(Gtk.Align.START)

        self.mode_cbtext = Gtk.ComboBoxText()
        self.mode_cbtext.set_property('hexpand', True)
        for m in modes:
            self.mode_cbtext.append_text(m)

        self.bitrate_spin = Gtk.SpinButton()
        self.bitrate_spin.set_property('hexpand', True)
        self.bitrate_spin.set_numeric(True)
        self.bitrate_spin.set_adjustment(bitrate)

        i = modes.index(conf.opus['mode'])
        self.mode_cbtext.set_active(i)
        self.bitrate_spin.set_value(conf.opus['bitrate'])

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(bitrate_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def _update_opus(self, button):
        m = self.mode_cbtext.get_active_text()
        b = self.bitrate_spin.get_value_as_int()

        conf.opus['mode'] = m
        conf.opus['bitrate'] = b

    def _vorbis(self):
        modes = ['CBR', 'ABR', 'VBR']
        bitrate = Gtk.Adjustment(160, 64, 500, 1, 10)
        quality = Gtk.Adjustment(5, 0, 10, 1, 10)

        mode_label = Gtk.Label('Mode')
        mode_label.set_halign(Gtk.Align.START)
        bitrate_label = Gtk.Label('Bitrate')
        bitrate_label.set_halign(Gtk.Align.START)
        quality_label = Gtk.Label('Quality')
        quality_label.set_halign(Gtk.Align.START)

        self.mode_cbtext = Gtk.ComboBoxText()
        self.mode_cbtext.set_property('hexpand', True)
        for m in modes:
            self.mode_cbtext.append_text(m)
        self.mode_cbtext.connect('changed', self.on_mode_changed)

        self.bitrate_spin = Gtk.SpinButton()
        self.bitrate_spin.set_property('hexpand', True)
        self.bitrate_spin.set_numeric(True)
        self.bitrate_spin.set_adjustment(bitrate)

        self.quality_spin = Gtk.SpinButton()
        self.quality_spin.set_property('hexpand', True)
        self.quality_spin.set_numeric(True)
        self.quality_spin.set_adjustment(quality)

        i = modes.index(conf.vorbis['mode'])
        self.mode_cbtext.set_active(i)
        self.bitrate_spin.set_value(conf.vorbis['bitrate'])
        self.quality_spin.set_value(conf.vorbis['quality'])

        self.grid.attach(mode_label, 0, 0, 1, 1)
        self.grid.attach_next_to(self.mode_cbtext, mode_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(bitrate_label, 0, 1, 1, 1)
        self.grid.attach_next_to(self.bitrate_spin, bitrate_label,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.grid.attach(quality_label, 0, 2, 1, 1)
        self.grid.attach_next_to(self.quality_spin, quality_label,
                                 Gtk.PositionType.RIGHT, 1, 1)

    def _update_vorbis(self, button):
        m = self.mode_cbtext.get_active_text()
        b = self.bitrate_spin.get_value_as_int()
        q = self.quality_spin.get_value_as_int()

        conf.vorbis['mode'] = m
        conf.vorbis['bitrate'] = b
        conf.vorbis['quality'] = q

    def on_mode_changed(self, combo):
        m = combo.get_active_text()
        if m == 'CBR' or m == 'ABR':
            self.bitrate_spin.set_sensitive(True)
            self.quality_spin.set_sensitive(False)
        elif m == 'VBR':
            self.bitrate_spin.set_sensitive(False)
            self.quality_spin.set_sensitive(True)

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

        for i in range(len(conf.filters)):
            active_type = conf.filters[i][0]
            active_name = conf.filters[i][1]

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
            for filter_type in FILTERS:
                type_cbtext.append_text(filter_type)

                if active_type == filter_type:
                    type_cbtext.set_active(j)

                    k = 0
                    for filter_name in FILTERS[filter_type]:
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

            if i == len(conf.filters) - 1:
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
        conf.filters.append(['', '', None])

        self._update_filters()

    def on_remove_clicked(self, button, i):
        conf.filters.pop(i)

        self._update_filters()

    def on_move_clicked(self, button, direction, i):
        if direction == 'up':
            conf.filters[i - 1:i + 1] = [conf.filters[i],
                                          conf.filters[i - 1]]
        elif direction == 'down':
            conf.filters[i:i + 2] = [conf.filters[i + 1],
                                      conf.filters[i]]
        self._update_filters()

    def on_type_changed(self, combo, i):
        t = combo.get_active_text()
        conf.filters[i][0] = t
        conf.filters[i][1] = ''
        conf.filters[i][2] = None

        self._update_filters()

    def on_name_changed(self, combo, t, i):
        n = combo.get_active_text()
        conf.filters[i][0] = t
        conf.filters[i][1] = n
        args = OrderedDict()
        if t == 'Resize':
            args['width'] = 0
            args['height'] = 0
        elif n == 'RemoveGrain':
            args['mode'] = [2]
        elif n == 'Trim':
            args['first'] = 0
            args['last'] = 0
        conf.filters[i][2] = args

        self._update_filters()

    def on_conf_clicked(self, button, t, n, i):
        if t in ['Source', 'Resize']:
            dlg = FilterDialog(self, t, i)
        else:
            dlg = FilterDialog(self, n, i)
        dlg.run()
        dlg.destroy()

class FilterDialog(Gtk.Dialog):

    def __init__(self, parent, flt, i):
        Gtk.Dialog.__init__(self, flt + ' settings', parent, 0)
        self.set_default_size(240, 0)

        button = self.add_button('_OK', Gtk.ResponseType.OK)

        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(6)
        self.grid.set_row_spacing(6)
        self.grid.set_property('margin', 6)

        box = self.get_content_area()
        box.add(self.grid)

        if flt == 'Source':
            self._source()
            button.connect('clicked', self._update_source)
        elif flt == 'CropAbs':
            self._crop(True, i)
            button.connect('clicked', self._update_crop, True, i)
        elif flt == 'CropRel':
            self._crop(False, i)
            button.connect('clicked', self._update_crop, False, i)
        elif flt == 'Resize':
            self._resize(i)
            button.connect('clicked', self._update_resize, i)
        elif flt == 'FluxSmoothT':
            self._fsmooth(False, i)
            button.connect('clicked', self._update_fsmooth, False, i)
        elif flt == 'FluxSmoothST':
            self._fsmooth(True, i)
            button.connect('clicked', self._update_fsmooth, True, i)
        elif flt == 'RemoveGrain':
            self._rgvs(i)
            button.connect('clicked', self._update_rgvs, i)
        elif flt == 'TemporalSoften':
            self._tsoft(i)
            button.connect('clicked', self._update_tsoft, i)
        elif flt == 'f3kdb':
            self._f3kdb(i)
            button.connect('clicked', self._update_f3kdb, i)
        elif flt == 'Trim':
            self._trim(i)
            button.connect('clicked', self._update_trim, i)

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

    def _update_source(self, button):
        flt = conf.filters[0][2]

        n = self.fpsnum_spin.get_value_as_int()
        d = self.fpsden_spin.get_value_as_int()

        if n != 0 or d != 1:
            flt['fpsnum'] = n
            flt['fpsden'] = d

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

    def _update_crop(self, button, absolute, i):
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
        self.width_spin.set_value(flt.get('width', 0))
        self.height_spin.set_value(flt.get('height', 0))
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

    def _update_resize(self, button, i):
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
        if not 0 in p:
            self.y_check.set_active(False)
        if not 1 in p:
            self.u_check.set_active(False)
        if not 2 in p:
            self.v_check.set_active(False)

        self.grid.attach(tt_label, 0, 0, 1, 1)
        self.grid.attach(self.tt_spin, 1, 0, 3, 1)
        self.grid.attach(st_label, 0, 1, 1, 1)
        self.grid.attach(self.st_spin, 1, 1, 3, 1)
        self.grid.attach(planes_label, 0, 2, 1, 1)
        self.grid.attach(self.y_check, 1, 2, 1, 1)
        self.grid.attach(self.u_check, 2, 2, 1, 1)
        self.grid.attach(self.v_check, 3, 2, 1, 1)

    def _update_fsmooth(self, button, spatial, i):
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

    def _update_rgvs(self, button, i):
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

    def _update_tsoft(self, button, i):
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
        self.depth_spin= Gtk.SpinButton()
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

    def _update_f3kdb(self, button, i):
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
        if od!= 8:
            flt['output_depth'] = od
        else:
            if 'output_depth' in flt:
                flt.pop('output_depth')
        if da!= 3 and od != 16:
            flt['dither_algo'] = da
        else:
            if 'dither_algo' in flt:
                flt.pop('dither_algo')
        if sm!= 2:
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

    def _trim(self):
        first_adj = Gtk.Adjustment(0, 0, 1000000, 1, 100)
        last_adj = Gtk.Adjustment(0, 0, 1000000, 1, 100)

        first_label = Gtk.Label('First')
        first_label.set_halign(Gtk.Align.START)
        last_label = Gtk.Label('Last')
        last_label.set_halign(Gtk.Align.START)

        self.first_spin = Gtk.SpinButton()
        self.first_spin.set_adjustment(fpsnum_adj)
        self.first_spin.set_numeric(True)
        self.first_spin.set_property('hexpand', True)
        self.last_spin = Gtk.SpinButton()
        self.last_spin.set_adjustment(fpsden_adj)
        self.last_spin.set_numeric(True)
        self.last_spin.set_property('hexpand', True)

        flt = conf.filters[0][2]
        self.first_spin.set_value(flt.get('first', 0))
        self.last_spin.set_value(flt.get('last', 0))

        self.grid.attach(first_label, 0, 0, 1, 1)
        self.grid.attach(self.first_spin, 1, 0, 1, 1)
        self.grid.attach(last_label, 0, 1, 1, 1)
        self.grid.attach(self.last_spin, 1, 1, 1, 1)

    def _update_trim(self, button):
        flt = conf.filters[0][2]

        f = self.first_spin.get_value_as_int()
        l = self.last_spin.get_value_as_int()

        flt['first'] = f
        flt['last'] = l

    def on_depth_changed(self, spin):
        if spin.get_value_as_int() == 16:
            self.dither_cbtext.set_sensitive(False)
        else:
            self.dither_cbtext.set_sensitive(True)

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
