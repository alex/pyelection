#!/usr/bin/env python

import gobject
import gtk
import gtk.glade
try:
    import pygtk
    pygtk.require('2.0')
except:
    pass
import threading

from models import StateResults
from states import STATES

gtk.gdk.threads_init()

def threaded(func):
    def decorator(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.start()
    return decorator

class pyelection(object):
    def __init__(self):
        # Set up glade stuff
        self.gladefile = 'pyelection.glade'
        self.wTree = gtk.glade.XML(self.gladefile, 'mainWindow')
        
        self.wTree.signal_autoconnect(self)
        
        # initiate widgets
        self.initiate_widgets()
    
    def initiate_widgets(self):
        # get the 3 tree views
        self.stateView = self.wTree.get_widget('stateView')
        self.resultView = self.wTree.get_widget('resultView')
        self.overallView = self.wTree.get_widget('overallView')
        
        # set up the list view and columns for the state tree view
        self.stateList = gtk.ListStore(gobject.TYPE_PYOBJECT, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_STRING)
        self.state_columns = []
        self.state_columns.append(('State', 1))
        self.state_columns.append(('Winner', 2))
        self.state_columns.append(('Reporting(%)', 3))
        self.state_columns.append(('Date', 4))
        for column in self.state_columns:
            col = gtk.TreeViewColumn(column[0], gtk.CellRendererText(), text=column[1])
            col.set_resizable(True)
            col.set_sort_column_id(column[1])
            self.stateView.append_column(col) 
        self.stateView.set_model(self.stateList)
        
        # set up the list view and columns for the result tree view
        self.resultList = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_INT)
        self.result_columns = []
        self.result_columns.append(('Name', 0))
        self.result_columns.append(('Votes', 1))
        self.result_columns.append(('Delegates', 2))
        for column in self.result_columns:
            col = gtk.TreeViewColumn(column[0], gtk.CellRendererText(), text=column[1])
            col.set_resizable(True)
            col.set_sort_column_id(column[1])
            self.resultView.append_column(col)
        self.resultView.set_model(self.resultList)
        
        # set up the list view and columns for the overall tree view
        self.overallList = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_INT)
        self.overall_columns = []
        self.overall_columns.append(('Name', 0))
        self.overall_columns.append(('Votes', 1))
        self.overall_columns.append(('Delegates', 2))
        for column in self.overall_columns:
            col = gtk.TreeViewColumn(column[0], gtk.CellRendererText(), text=column[1])
            col.set_resizable(True)
            col.set_sort_column_id(column[1])
            self.overallView.append_column(col)
        self.overallView.set_model(self.overallList)
        
        # get the progress bar
        self.progress = self.wTree.get_widget('updateBar')
    
    def party_changed(self, widget):
        self.clear_states()
        # get the selected party
        active = widget.get_model().get_value(widget.get_active_iter(), 0)
        if active == 'Democrats':
            party = 'D'
        else:
            party = 'R'
        self.total = len(STATES)
        self.count = float(0)
        
        text = 'Updated %d of %d states: %.0f%% done'
        self.refresh_progress_bar(text)
        for state in STATES:
            self.add_state(state[0], state[1], party, count=True)
    
    def state_changed(self, widget):
        self.refresh_results()
    
    def refresh(self, widget):
        self.total = len(list(self.iter_states()))
        self.count = float(0)
        
        text = 'Updated %d of %d states: %.0f%% done'
        self.refresh_progress_bar(text)
        for itera, state in self.iter_states():
            self.update_single(itera, count=True)
    
    def refresh_selected(self, widget):
        model, itera = self.stateView.get_selection().get_selected()
        
        self.update_single(itera)
        self.refresh_results()
    
    def custom_refresh(self, widget):
        states = list(self.iter_states())
        dlg = CustomRefreshDlg(states)
        result = dlg.run()
        [self.update_single(itera) for itera, state in result]
        self.refresh_results()
    
    @threaded
    def add_state(self, abbr, name, party, count=False):
        state = StateResults(abbr, name, party)
        
        gtk.gdk.threads_enter()
        self.stateList.append(state.get_list())
        gtk.gdk.threads_leave()
        
        if count:
            self.count += 1
        self.refresh_overall()
    
    @threaded
    def update_single(self, itera, count=False):
        gtk.gdk.threads_enter()
        state = self.stateList.get_value(itera, 0)
        gtk.gdk.threads_leave()
        
        state.refresh()
        info = state.get_list()
        
        gtk.gdk.threads_enter()
        self.stateList.set(itera,
            0, info[0],
            1, info[1],
            2, info[2],
            3, info[3],
            4, info[4]
        )
        gtk.gdk.threads_leave()
        if count:
            self.count += 1
        self.refresh_overall()
    
    @threaded
    def refresh_progress_bar(self, template):
        percent = self.count/self.total
        while percent != 1 or percent != 1.0:
            percent = self.count/self.total
            text = template % (self.count, self.total, percent*100)
            gtk.gdk.threads_enter()
            self.progress.set_fraction(percent)
            if percent == 1 or percent == 1.0:
                self.progress.set_text('Done')
            else:
                self.progress.set_text(text)
            gtk.gdk.threads_leave()
    
    @threaded
    def refresh_results(self):
        gtk.gdk.threads_enter()
        self.clear_results()
        model, itera = self.stateView.get_selection().get_selected()
        
        if itera:
            state = self.stateList.get_value(itera, 0)
            for candidate in state.candidates:
                self.resultList.append([candidate['name'], candidate['votes'], candidate['delegates']])
        gtk.gdk.threads_leave()
    
    def refresh_overall(self):
        info = {}
        for itera, state in self.iter_states():
            for candidate in state.candidates:
                if candidate['delegates'] > 0:
                    if info.has_key(candidate['name']):
                        info[candidate['name']]['delegates'] += candidate['delegates']
                        info[candidate['name']]['votes'] += candidate['votes']
                    else:
                        info[candidate['name']] = {}
                        info[candidate['name']]['name'] = candidate['name']
                        info[candidate['name']]['delegates'] = candidate['delegates']
                        info[candidate['name']]['votes'] = candidate['votes']
        self.clear_overall()
        for cand in info.itervalues():
            self.overallList.append([cand['name'], cand['votes'], cand['delegates']])
    
    def iter_states(self):
        for row in self.stateList:
            yield row.iter, row[0]
    
    def clear_states(self):
        self.stateList.clear()
    
    def clear_results(self):
        self.resultList.clear()
    
    def clear_overall(self):
        self.overallList.clear()
    
    def quit(self, *args, **kwargs):
        gtk.main_quit()

class CustomRefreshDlg(object):
    def __init__(self, states):
        self.gladefile = 'pyelection.glade'
        self.states = states
        
        self.wTree = gtk.glade.XML(self.gladefile, 'stateSelectorDlg')
        self.wTree.signal_autoconnect(self)
        self.dlg = self.wTree.get_widget('stateSelectorDlg')
        
        self.stateArea = self.wTree.get_widget('boxStateSelector')
        
        for itera, state in self.states:
            cbox = gtk.CheckButton(label=state.name)
            self.stateArea.pack_start(cbox)
        
        self.dlg.show_all()
    
    def run(self):
        result = self.dlg.run()
        
        if result == gtk.RESPONSE_OK:
            active = [self.states[num] for num, chbox in enumerate(self.stateArea.get_children()) if chbox.get_active()]
        else:
            active = []
        self.dlg.destroy()
        return active

if __name__ == '__main__':
    app = pyelection()
    gtk.gdk.threads_enter()
    gtk.main()
    gtk.gdk.threads_leave()
