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

gobject.threads_init()


class pyelection(object):
    def __init__(self):
        self.gladefile = 'pyelection.glade'
        self.wTree = gtk.glade.XML(self.gladefile, 'mainWindow')
        
        self.wTree.signal_autoconnect(self)
        
        self.initiate_widgets()
        
        self.refreshing = False
        
        self.active_processes = []
    
    def initiate_widgets(self):
        self.stateView = self.wTree.get_widget('stateView')
        self.resultView = self.wTree.get_widget('resultView')
        self.overallView = self.wTree.get_widget('overallView')
        
        
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
        
        self.overallList = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT)
        self.overall_columns = []
        self.overall_columns.append(('Name', 0))
        self.overall_columns.append(('Delegates', 1))
        for column in self.overall_columns:
            col = gtk.TreeViewColumn(column[0], gtk.CellRendererText(), text=column[1])
            col.set_resizable(True)
            col.set_sort_column_id(column[1])
            self.overallView.append_column(col)
        self.overallView.set_model(self.overallList)
        
        self.progress = self.wTree.get_widget('updateBar')
        self.progress_percent = 0
        self.progress_text = 'Not currently doing anything'
    
    def party_changed(self, widget):
        self.clear_states()
        active = widget.get_model().get_value(widget.get_active_iter(), 0)
        if active == 'Democrats':
            party = 'D'
        else:
            party = 'R'
        self.stop_refresh()
        self.idle_func(self.set_states(party))
    
    def set_states(self, party):
        if not self.refreshing:
            self.refreshing = True
            num = len(STATES)
            for count, state in enumerate(STATES):
                state = StateResults(state[0], state[1], party)
                self.stateList.append(state.get_list())
                
                count = float(count+1)
                self.progress_text = 'Updated %d of %d states: %.0f%% done' % (count, num, count/num*100)
                self.progress_percent = count / num
                yield True
            self.overall_update()
            self.refreshing = False
            yield False
        
    def state_changed(self, *args):
        self.clear_results()
        selection = self.stateView.get_selection()
        
        model, selection_iter = selection.get_selected()
        
        if selection_iter:
            state = self.stateList.get_value(selection_iter, 0)
            
            for candidate in state.candidates:
                self.resultList.append([candidate['name'], candidate['votes'], candidate['delegates']])
    
    def refresh(self, widget):
        self.idle_func(self.update_states())
    
    def refresh_selected(self, widget):
        selection = self.stateView.get_selection()
        model, selection_iter = selection.get_selected()
        
        self.refresh_single(selection_iter)
        self.state_changed()
    
    def refresh_single(self, itera):
        state = self.stateList.get_value(itera, 0)
        state.refresh()
        info = state.get_list()
        self.stateList.set(itera,
            0, info[0],
            1, info[1],
            2, info[2],
            3, info[3],
            4, info[4]
        )
    
    def update_states(self):
        if not self.refreshing:
            self.refreshing = True
            num = len(app.stateList)
            for count, (itera, state) in enumerate(self.iter_states()):
                self.refresh_single(itera)
                
                count = float(count+1)
                self.progress_text = 'Updated %d of %d states: %.0f%% done' % (count, num, count/num*100)
                self.progress_percent = count / num
                yield True
            self.overall_update()
            self.refreshing = False
            yield False
    
    def overall_update(self):
        self.clear_overall()
        info = {}
        for itera, state in self.iter_states():
            for candidate in state.candidates:
                if candidate['delegates'] > 0:
                    if info.has_key(candidate['name']):
                        info[candidate['name']]['delegates'] += candidate['delegates']
                    else:
                        info[candidate['name']] = {}
                        info[candidate['name']]['name'] = candidate['name']
                        info[candidate['name']]['delegates'] = candidate['delegates']
        for cand in info.itervalues():
            self.overallList.append([cand['name'], cand['delegates']])
    
    def custom_refresh(self, widget):
        states = []
        for itera, state in self.iter_states():
            states.append((state, itera))
        dlg = CustomRefreshDlg(states)
        result = dlg.run()
        [self.refresh_single(itera) for state, itera in result]
        self.overall_update()
        self.state_changed()
    
    def idle_func(self, func):
        proc_id = gobject.idle_add(func.next)
        self.active_processes.append(proc_id)
        gobject.timeout_add(500, self.progress_update)       
        
    def progress_update(self):
        self.progress.set_fraction(self.progress_percent)
        if self.progress_percent == 1.0 or self.progress_percent == 1:
            self.progress.set_text('Done')
            return False
        self.progress.set_text(self.progress_text)
        return True
    
    def stop_refresh(self, *args):
        remaining = filter(gobject.source_remove, self.active_processes)
        self.active_processes = [x for x in self.active_processes if x not in remaining]
        if not self.active_processes:
            self.refreshing = False
    
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
    
    def run(self):
        self.wTree = gtk.glade.XML(self.gladefile, 'stateSelectorDlg')
        self.wTree.signal_autoconnect(self)
        self.dlg = self.wTree.get_widget('stateSelectorDlg')
        
        self.stateArea = self.wTree.get_widget('boxStateSelector')
        
        for state, itera in self.states:
            cbox = gtk.CheckButton(label=state.name)
            self.stateArea.pack_start(cbox)
        
        self.dlg.show_all()
        
        result = self.dlg.run()
        
        if result == gtk.RESPONSE_OK:
            active = [self.states[num] for num, chbox in enumerate(self.stateArea.get_children()) if chbox.get_active()]
        
        self.dlg.destroy()
        return active


if __name__ == '__main__':
    app = pyelection()
    gtk.main()
