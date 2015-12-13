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
            # Set up single worker thread
            self.idle = True
            self.worker = ThreadPoolExecutor(max_workers=1)
            self.worker.submit(self.wait)
            # Initialize a thread lock and acquire it
            self.lock = Lock()
            self.lock.acquire()
            # Future lists
            self.tstore = Gtk.TreeStore(GObject.TYPE_PYOBJECT, str, str, str)
            self.waitlist = []
            # Running proc
            self.proc = None

            Notify.init('pyanimenc')
            Queue.__init = True

    def wait(self):
        if self.idle:
            self.lock.acquire()

    def update(self):
        for job in self.tstore:
            status = self.tstore.get_value(job.iter, 3)
            filename = self.tstore.get_value(job.iter, 1)
            new_status = self._mark_steps(job)
            GLib.idle_add(self.tstore.set_value, job.iter, 3, new_status)
            if new_status == 'Done' and not job.next:
                # Mark as idle if it was the last job
                GLib.idle_add(self._notify, 'Jobs done')
                self.idle = True
                self.queue_start_button.set_sensitive(False)
                self.queue_stop_button.set_sensitive(False)
                self.queue_clr_button.set_sensitive(True)
            elif new_status == 'Running' and new_status != status:
                GLib.idle_add(self._notify, 'Processing ' + filename)

    def _mark_steps(self, job):
        for step in job.iterchildren():
            future = self.tstore.get_value(step.iter, 0)
            status = self.tstore.get_value(step.iter, 3)
            if status == 'Failed':
                return 'Failed'
            elif future.done():
                # Mark done steps as such
                GLib.idle_add(self.tstore.set_value, step.iter, 3, 'Done')
                if not step.next:
                    # Mark job as done if all steps are
                    return 'Done'
            elif future.running():
                # Mark running step as such
                GLib.idle_add(self.tstore.set_value, step.iter, 3, 'Running')
                return 'Running'
            else:
                return 'Waiting'

    def _notify(self, text):
        n = Notify.Notification.new('pyanimenc', text, 'dialog-information')
        n.set_urgency(1)
        n.show()

# vim: ts=4 sw=4 et:
