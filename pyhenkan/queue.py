from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import GLib, GObject, Gtk, Notify


class Queue:
    # Singleton
    __instance = None
    __init = False

    def __new__(cls):
        if Queue.__instance is None:
            Queue.__instance = object.__new__(cls)
        return Queue.__instance

    def __init__(self):
        if not Queue.__init:
            Queue.__init = True
            # Set up single worker thread
            self.idle = True
            self.executor = ThreadPoolExecutor(max_workers=1)
            # Initialize a thread lock and acquire it
            self.lock = Lock()
            self.lock.acquire()
            # Lock the queue
            future = self.executor.submit(self.wait)
            # Keep a list of all potential locks
            self.waitlist = [future]
            # Running proc
            self.proc = None

            # GUI
            expander_crpixbuf = Gtk.CellRendererPixbuf()
            expander_crpixbuf.set_property('is-expander', True)
            expander_tvcolumn = Gtk.TreeViewColumn('', expander_crpixbuf)

            input_crtext = Gtk.CellRendererText()
            input_tvcolumn = Gtk.TreeViewColumn('Input', input_crtext, text=1)

            output_crtext = Gtk.CellRendererText()
            output_tvcolumn = Gtk.TreeViewColumn('Output', output_crtext,
                                                 text=2)

            codec_crtext = Gtk.CellRendererText()
            codec_tvcolumn = Gtk.TreeViewColumn('Codec', codec_crtext, text=3)

            status_crtext = Gtk.CellRendererText()
            status_tvcolumn = Gtk.TreeViewColumn('Status', status_crtext,
                                                 text=4)

            self.tstore = Gtk.TreeStore(GObject.TYPE_PYOBJECT,
                                        str, str, str, str)

            tview = Gtk.TreeView(self.tstore)
            tview.append_column(expander_tvcolumn)
            tview.append_column(input_tvcolumn)
            tview.append_column(output_tvcolumn)
            tview.append_column(codec_tvcolumn)
            tview.append_column(status_tvcolumn)

            self.tselection = tview.get_selection()

            scrwin = Gtk.ScrolledWindow()
            scrwin.set_policy(Gtk.PolicyType.AUTOMATIC,
                              Gtk.PolicyType.ALWAYS)
            scrwin.add(tview)

            self.start_button = Gtk.Button()
            self.start_button.set_label('Start')
            self.start_button.connect('clicked', self.on_start_clicked)
            self.start_button.set_sensitive(False)

            self.stop_button = Gtk.Button()
            self.stop_button.set_label('Stop')
            self.stop_button.connect('clicked', self.on_stop_clicked)
            self.stop_button.set_sensitive(False)

            self.delete_button = Gtk.Button()
            self.delete_button.set_label('Delete')
            self.delete_button.connect('clicked', self.on_delete_clicked)
            self.delete_button.set_sensitive(False)

            self.clear_button = Gtk.Button()
            self.clear_button.set_label('Clear')
            self.clear_button.connect('clicked', self.on_clear_clicked)
            self.clear_button.set_sensitive(False)

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                           spacing=6)
            hbox.pack_start(self.start_button, True, True, 0)
            hbox.pack_start(self.stop_button, True, True, 0)
            hbox.pack_start(self.delete_button, True, True, 0)
            hbox.pack_start(self.clear_button, True, True, 0)

            self.pbar = Gtk.ProgressBar()
            self.pbar.set_property('margin', 6)
            self.pbar.set_text('Ready')
            self.pbar.set_show_text(True)

            self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                spacing=6)
            self.vbox.set_property('margin', 6)
            self.vbox.pack_start(scrwin, True, True, 0)
            self.vbox.pack_start(hbox, False, True, 0)

            # Notifications
            Notify.init('pyhenkan')

    def on_start_clicked(self, button):
        if len(self.tstore):
            self.stop_button.set_sensitive(True)
            self.delete_button.set_sensitive(False)
            self.clear_button.set_sensitive(False)
            print('Start processing...')
            self.idle = False
            self.lock.release()

    def on_stop_clicked(self, button):
        self.idle = True
        print('Stop processing...')
        # Wait for the process to terminate
        while self.proc.poll() is None:
            self.proc.terminate()

        for job in self.tstore:
            status = self.tstore.get_value(job.iter, 4)
            if status == 'Running':
                for step in job.iterchildren():
                    future = self.tstore.get_value(step.iter, 0)
                    # Cancel and mark steps as failed
                    if not future.done():
                        self.tstore.set_value(step.iter, 4, 'Failed')
                        future.cancel()
                # Mark job as failed
                self.tstore.set_value(job.iter, 4, 'Failed')

        self.pbar.set_fraction(0)
        self.pbar.set_text('Ready')
        self.stop_button.set_sensitive(False)
        self.clear_button.set_sensitive(True)

    def on_delete_clicked(self, button):
        job = self.tselection.get_selected()[1]
        # If child, select parent instead
        if self.tstore.iter_depth(job) == 1:
            job = self.tstore.iter_parent(job)
        status = self.tstore.get_value(job, 4)
        while self.tstore.iter_has_child(job):
            step = self.tstore.iter_nth_child(job, 0)
            future = self.tstore.get_value(step, 0)
            # Cancel pending step
            if not future.done():
                future.cancel()
            self.tstore.remove(step)
        # Cancel associated wait job
        if status not in ['Done', 'Failed']:
            i = self.tstore.get_path(job).get_indices()[0]
            self.waitlist[i].cancel()
        # Delete job
        self.tstore.remove(job)

        if not len(self.tstore):
            self.start_button.set_sensitive(False)
            self.delete_button.set_sensitive(False)
            self.clear_button.set_sensitive(False)

    def on_clear_clicked(self, button):
        for job in self.tstore:
            # Cancel jobs before clearing them
            for step in job.iterchildren():
                future = self.tstore.get_value(step.iter, 0)
                future.cancel()
            for future in self.waitlist:
                future.cancel()
        # Clear queue
        self.tstore.clear()

        self.start_button.set_sensitive(False)
        self.delete_button.set_sensitive(False)
        self.clear_button.set_sensitive(False)

    def wait(self):
        if self.idle:
            self.lock.acquire()

    def update(self):
        for job in self.tstore:
            status = self.tstore.get_value(job.iter, 4)
            filename = self.tstore.get_value(job.iter, 1)
            new_status = self._mark_steps(job)
            GLib.idle_add(self.tstore.set_value, job.iter, 4, new_status)
            if new_status == 'Done' and not job.next:
                # Mark as idle if it was the last job
                GLib.idle_add(self._notify, 'Jobs done')
                self.idle = True
                self.start_button.set_sensitive(False)
                self.stop_button.set_sensitive(False)
                self.clear_button.set_sensitive(True)
            elif new_status == 'Running' and new_status != status:
                GLib.idle_add(self._notify, 'Processing ' + filename)

    def _mark_steps(self, job):
        for step in job.iterchildren():
            future = self.tstore.get_value(step.iter, 0)
            status = self.tstore.get_value(step.iter, 4)
            if status == 'Failed':
                return 'Failed'
            elif future.done():
                # Mark done steps as such
                GLib.idle_add(self.tstore.set_value, step.iter, 4, 'Done')
                if not step.next:
                    # Mark job as done if all steps are
                    return 'Done'
            elif future.running():
                # Mark running step as such
                GLib.idle_add(self.tstore.set_value, step.iter, 4, 'Running')
                return 'Running'
            else:
                return 'Waiting'

    def _notify(self, text):
        n = Notify.Notification.new('pyhenkan', text, 'dialog-information')
        n.set_urgency(1)
        n.show()

# vim: ts=4 sw=4 et:
