#!/usr/bin/python -tt
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>

'''
Tools for helping Fedora package reviewers
'''

from bugzilla import Bugzilla

BZ_URL='https://bugzilla.redhat.com/xmlrpc.cgi'

from reviewtools import Helpers

class ReviewBug(Helpers):
    def __init__(self,bug,user=None,password=None):
        self.bug_num = bug
        self.spec_url = None
        self.srpm_url = None
        self.spec_file = None
        self.srpm_file = None
        self.bugzilla = Bugzilla(url=BZ_URL)
        self.login = False
        if user and password:
            self.bugzilla.login(user=user, password=password)
            self.login = True
        self.user = user
        self.bug = self.bugzilla.getbug(self.bug_num)

    def find_urls(self):
        if self.bug.longdescs:
            for c in self.bug.longdescs:
                body = c['body']
                urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', body)
                if urls:
                    for url in urls:
                        if url.endswith(".spec"):
                            self.spec_url = url
                        elif url.endswith(".src.rpm"):

                            self.srpm_url = url

    def assign_bug(self):    
        if self.login:
            self.bug.setstatus('ASSIGNED')
            self.bug.setassignee(assigned_to=self.user)
            self.bug.addcomment('I will review this bug')
            flags = {'fedora-review' : '?'}
            self.bug.updateflags(flags)
            self.bug.addcc([self.user])
        else:
            print("You need to login before assigning a bug")

    def add_comment(self,comment):    
        if self.login:
            self.bug.addcomment(comment)
        else:
            print("You need to login before commenting on a bug")

    def add_comment_from_file(self,fname):
        fd = open(fname,"r")
        lines = fd.readlines()
        fd.close
        self.add_comment("".join(lines))
                            
    def download_files(self):
        if self.spec_url and self.srpm_url:
            self.spec_file = self._get_file(self.spec_url)
            self.srpm_file = self._get_file(self.srpm_url)
            if self.spec_file and self.srpm_file:
                return True
        return False

    
