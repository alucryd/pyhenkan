import re
import subprocess

from gi.repository import GLib


class Mux:
    def __init__(self, mediafile, pbar):
        self.mediafile = mediafile
        self.pbar = pbar
        self.proc = None

    def mux(self):
        print('Mux...')
        i = self.mediafile.path
        o = '/'.join([self.mediafile.dname, self.mediafile.oname])
        o = '_'.join([o, self.mediafile.osuffix])
        o = '.'.join([o, self.mediafile.ocont])
        uid = self.mediafile.uid

        if self.mediafile.ocont == 'mkv':
            cmd = self._mkv(i, o, uid)
            print(cmd)
            self.proc = subprocess.Popen(cmd, shell=True,
                                         stdout=subprocess.PIPE,
                                         universal_newlines=True)
            self._mkv_progress()

    def _mkv(self, i, o, uid):
        cmd = ['mkvmerge -o "{}" -D -A -S -B -T "{}"'.format(o, i)]

        for t in self.mediafile.tracklist:
            if t.type == 'Video' and t.enable:
                f = '-A -S -B -T -M -d {} --no-global-tags --no-chapters '
                f += '--track-name {}:"{}" --language {}:"{}" "{}"'
            elif t.type == 'Audio' and t.enable:
                f = '-D -S -B -T -M -a {} --no-global-tags --no-chapters '
                f += '--track-name {}:"{}" --language {}:"{}" "{}"'
            elif t.type == 'Text' and t.enable:
                f = '-D -A -B -T -M -s {} --no-global-tags --no-chapters '
                f += '--track-name {}:"{}" --language {}:"{}" "{}"'
            elif t.type == 'Menu' and t.enable:
                f = '-D -A -S -T -M -b {} --no-global-tags --no-chapters '
                f += '--track-name {}:"{}" --language {}:"{}" "{}"'
            f = f.format(t.id, t.id, t.title, t.id, t.lang,
                         t.tmpfilepath if t.tmpfilepath else t.file.path)
            cmd.append(f)

        if uid:
            u = '--segment-uid ' + uid
            cmd.append(u)

        cmd = ' '.join(cmd)

        return cmd

    def _mkv_progress(self):
        GLib.idle_add(self.pbar.set_fraction, 0)
        GLib.idle_add(self.pbar.set_text, 'Muxing...')
        while self.proc.poll() is None:
            line = self.proc.stdout.readline()
            if 'Progress:' in line:
                f = int(re.findall('[0-9]+', line)[0]) / 100
                GLib.idle_add(self.pbar.set_fraction, f)
        if self.proc.poll() < 0:
            GLib.idle_add(self.pbar.set_text, 'Failed')
        else:
            GLib.idle_add(self.pbar.set_text, 'Ready')
        GLib.idle_add(self.pbar.set_fraction, 0)
