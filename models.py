import BeautifulSoup
import datetime
import re
import time
import urllib

RESULT_URL = 'http://politics.nytimes.com/election-guide/2008/results/states/%s.html'

class StateResults(object):
    def __init__(self, abbr, name, party='D'):
        self.abbr = abbr
        self.name = name
        if party not in 'DR':
            raise ValueError, "Party should be either 'D' or 'R'."
        self.party = party
        
        self.candidates = []
        
        self.url = RESULT_URL % self.abbr
        
        self.refresh()
    
    def __unicode__(self):
        return u'<StateResults state=%s>' % self.name
    
    def __str__(self):
        return str(self.__unicode__())
    
    def __repr__(self):
        return repr(self.__unicode__())
    
    def __eq__(self, other):
        return self.name == other.name and self.candidates == other.candidates
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def refresh(self):
        self.page = urllib.urlopen(self.url).read()
        self.page = BeautifulSoup.BeautifulSoup(self.page)
        
        try:
            if self.party == 'D':
                area = self.page.find(attrs={'class': 'subcolumn-a results'})
                date_area = self.page.find(attrs={'class': 'subcolumn-a'}).find(attrs={'class': 'minor_subcolumn-a'}).contents[1].contents[0].strip()
            else:
                area = self.page.find(attrs={'class': 'subcolumn-b results'})
                date_area = self.page.find(attrs={'class': 'subcolumn-b'}).find(attrs={'class': 'minor_subcolumn-a'}).contents[1].contents[0].strip()
        except:
            pass
        
        try:
            self.reporting = int(area.find(attrs={'class': 'footer-note'}).contents[0].split('%')[0].strip())
        except:
            self.reporting = 0
        
        try:
            self.candidates = []
            
            candidates = area.find(attrs={'class': re.compile(r'^results')}).findAll(attrs={'class': re.compile(r'^candidate')})
            
            for candidate in candidates:
                par = candidate.parent
                info = {}
                info['name'] = par.findChildren()[0].contents[0].strip()
                info['votes'] = int(''.join(par.findChildren()[1].contents[0].strip().split(',')))
                try:
                    info['delegates'] = int(par.findChildren()[3].contents[0].strip())
                except:
                    info['delegates'] = 0
                self.candidates.append(info)
        except:
            self.candidates.append({'name': 'No results yet', 'votes': 0, 'delegates': 0})
        
        try:
            date = time.strptime(date_area, '%B %d, %Y')
            self.date = datetime.date(*date[:3])
        except:
            self.date = None
        
    
    def _get_winner(self):
        winner = {
            'votes': -1,
            'delegates': -1
        }
        for candidate in self.candidates:
            if candidate['delegates'] > winner['delegates'] or (candidate['delegates'] == winner['delegates'] and candidate['votes'] > winner['votes']):
                winner = candidate
        return winner
    winner = property(_get_winner)
    
    def _get_date_text(self):
        if self.date:
            return self.date.strftime('%m-%d-%Y')
        else:
            return 'Future'
    date_text = property(_get_date_text)
    
    def get_list(self):
        return [self, self.name, self.winner['name'], self.reporting, self.date_text]
