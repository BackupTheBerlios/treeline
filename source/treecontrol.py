#!/usr/bin/env python

#****************************************************************************
# treecontrol.py, provides a class for control of the main windows
#
# TreeLine, an information storage program
# Copyright (C) 2009, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#****************************************************************************

import sys
import os.path
from PyQt4 import QtCore, QtGui
try:
    from __main__ import __version__, iconPath
except ImportError:
    __version__ = '??'
    iconPath = None
import globalref
import treemainwin
import option
import optiondefaults
import icondict
import recentfiles


class TreeControl(object):
    """Program and main window control"""
    def __init__(self, userStyle):
        self.windowList = []
        globalref.treeControl = self
        mainVersion = '.'.join(__version__.split('.')[:2])
        globalref.options = option.Option(u'treeline-%s' % mainVersion, 21)
        globalref.options.loadAll(optiondefaults.defaultOutput())
        iconPathList = [iconPath, os.path.join(globalref.modPath, u'icons/'),
                        os.path.join(globalref.modPath, u'../icons/')]
        if not iconPath:
            del iconPathList[0]
        globalref.treeIcons = icondict.IconDict()
        globalref.treeIcons.addIconPath([os.path.join(path, u'tree') for path
                                         in iconPathList])
        globalref.treeIcons.addIconPath([globalref.options.iconPath])
        treemainwin.TreeMainWin.toolIcons = icondict.IconDict()
        treemainwin.TreeMainWin.toolIcons.\
                    addIconPath([os.path.join(path, u'toolbar')
                                 for path in iconPathList],
                                [u'', u'32x32', u'16x16'])
        treemainwin.TreeMainWin.toolIcons.loadAllIcons()
        windowIcon = globalref.treeIcons.getIcon(u'treeline')
        if windowIcon:
            QtGui.QApplication.setWindowIcon(windowIcon)
        if not userStyle:
            if sys.platform.startswith('dar'):
                QtGui.QApplication.setStyle('macintosh')
            elif not sys.platform.startswith('win'):
                QtGui.QApplication.setStyle('plastique')
        self.recentFiles = recentfiles.RecentFileList()
        qApp = QtGui.QApplication.instance()
        qApp.connect(qApp, QtCore.SIGNAL('focusChanged(QWidget*, QWidget*)'),
                     self.updateFocus)

    def firstWindow(self, fileNames=None):
        """Open first main window"""
        win = treemainwin.TreeMainWin()
        self.windowList.append(win)
        if fileNames:
            win.openFile(unicode(fileNames[0], globalref.localTextEncoding))
        else:
            self.autoOpen(win)
        win.show()

    def autoOpen(self, win):
        """Open last used file"""
        if globalref.options.boolData('AutoFileOpen') and \
                 self.recentFiles:
            path = self.recentFiles[0].path
            if path and not win.openFile(path, False):
                self.recentFiles.removeEntry(path)
        elif not self.recentFiles and \
                globalref.options.intData('RecentFiles', 0, 99):
            win.show()
            win.fileNew()   # prompt for template if no recent files

    def recentOpen(self, filePath):
        """Open from recentFiles call"""
        if filePath and globalref.mainWin.savePrompt():
            if not globalref.mainWin.openFile(filePath):
                self.recentFiles.removeEntry(filePath)

    def updateFocus(self):
        """Check for focus change to a different main window"""
        win = QtGui.QApplication.activeWindow()
        while win and win.parent():
            win = win.parent()
        try:
            win = win.mainWinRef
        except AttributeError:
            pass
        if win and win != globalref.mainWin:
            print 'Possible focus change', win
