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
import treedoc
import treemainwin
import treedialogs
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
            self.openFile(unicode(fileNames[0], globalref.localTextEncoding))
        else:
            self.autoOpen()
        win.show()

    def autoOpen(self):
        """Open last used file"""
        if globalref.options.boolData('AutoFileOpen') and \
                 self.recentFiles:
            path = self.recentFiles[0].path
            if path and not self.openFile(path, False):
                self.recentFiles.removeEntry(path)
        elif not self.recentFiles and \
                globalref.options.intData('RecentFiles', 0, 99):
            globalref.mainWin.show()
            globalref.mainWin.fileNew()  # tmplate prompt if no recent files

    def recentOpen(self, filePath):
        """Open from recentFiles call"""
        if filePath and self.savePrompt():
            if not self.openFile(filePath):
                self.recentFiles.removeEntry(filePath)

    def openFile(self, filePath, importOnFail=True, addToRecent=True):
        """Open given file, fail quietly if not importOnFail,
           return False if file should be removed from recent list,
           True otherwise"""
        if not self.checkAutoSave():
            return True
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        win = globalref.mainWin
        try:
            win.doc = treedoc.TreeDoc(filePath)
            win.fileImported = False
        except treedoc.PasswordError:
            QtGui.QApplication.restoreOverrideCursor()
            dlg = treedialogs.PasswordEntry(False, win)
            if dlg.exec_() != QtGui.QDialog.Accepted:
                return True
            win.doc.setPassword(filePath, dlg.password)
            result = self.openFile(filePath, importOnFail)
            if not dlg.saveIt:
                win.doc.clearPassword(filePath)
            return result
        except (IOError, UnicodeError):
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(win, 'TreeLine',
                              _('Error - could not read file "%s"') % filePath)
            return False
        except treedoc.ReadFileError, e:
            QtGui.QApplication.restoreOverrideCursor()
            if not importOnFail:
                return True
            # assume file is not a TreeLine file
            importType = self.chooseImportType()
            if not importType:
                return True
            try:
                QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                win.doc = treedoc.TreeDoc(filePath, False, importType)
            except treedoc.ReadFileError, e:
                QtGui.QApplication.restoreOverrideCursor()
                QtGui.QMessageBox.warning(win, 'TreeLine', _('Error - %s') % e)
                return False
            win.fileImported = True
        win.doc.root.open = True
        QtGui.QApplication.restoreOverrideCursor()
        win.updateForFileChange(addToRecent)
        if win.pluginInterface:
            win.pluginInterface.execCallback(win.pluginInterface.
                                             fileOpenCallbacks)
        return True

    def chooseImportType(self):
        """Show dialog for selecting file import type"""
        choices = [(_('Tab &indented text, one node per line'),
                    treedoc.tabbedImport),
                    (_('Text &table with header row, one node per line'),
                     treedoc.tableImport),
                    (_('Plain text, one &node per line (CR delimitted)'),
                     treedoc.textLineImport),
                    (_('Plain text &paragraphs (blank line delimitted)'),
                     treedoc.textParaImport),
                    (_('Treepad &file (text nodes only)'),
                     treedoc.treepadImport),
                    (_('&XML bookmarks (XBEL format)'), treedoc.xbelImport),
                    (_('&HTML bookmarks (Mozilla format)'),
                     treedoc.mozillaImport),
                    (_('&Generic XML (Non-TreeLine file)'),
                     treedoc.xmlImport),
                    (_('Open Document (ODF) text'), treedoc.odfImport)]
        dlg = treedialogs.RadioChoiceDlg(_('Import Text'),
                                         _('Choose Text Import Method'),
                                         choices, self)
        if dlg.exec_() != QtGui.QDialog.Accepted:
            return None
        return dlg.getResult()

    def newFile(self, templatePath=''):
        """Open a new file"""
        win = globalref.mainWin
        if templatePath:
            try:
                win.doc = treedoc.TreeDoc(templatePath)
                win.doc.root.open = True
                win.doc.fileName = ''
                win.doc.fileInfoFormat.updateFileInfo()
            except (treedoc.PasswordError, IOError, UnicodeError,
                    treedoc.ReadFileError):
                QtGui.QMessageBox.warning(win, 'TreeLine',
                            _('Error - could not read template file "%s"') \
                            % templatePath)
                win.doc = treedoc.TreeDoc()
        else:
            win.doc = treedoc.TreeDoc()
        win.updateForFileChange(False)

    def checkAutoSave(self):
        """Check for presence of auto save file & prompt user,
           return True if OK to continue"""
        if not globalref.options.intData('AutoSaveMinutes', 0, 999):
            return True
        autoSaveFile = self.autoSaveFilePath(filePath)
        if autoSaveFile:
            ans = QtGui.QMessageBox.information(self, 'TreeLine',
                                                _('Backup file "%s" exists.\n'\
                                                  'A previous session may '\
                                                  'have crashed.') %
                                                autoSaveFile,
                                                _('&Restore Backup'),
                                                _('&Delete Backup'),
                                                _('&Cancel File Open'), 0, 2)
            if ans == 0:
                if not self.restoreAutoSaveFile(filePath):
                    QtGui.QMessageBox.warning(self, 'TreeLine',
                                              _('Error - could not restore '\
                                                'backup'))
                return False
            elif ans == 1:
                self.delAutoSaveFile(filePath)
                return True
            else:
                return False

    def autoSaveFilePath(self, baseName=''):
        """Return the path to a backup file if it exists"""
        filePath = baseName and baseName or globalref.docRef.fileName
        filePath = filePath + '~'
        if len(filePath) > 1 and \
                 os.access(filePath.encode(sys.getfilesystemencoding()),
                           os.R_OK):
            return filePath
        return ''

    def delAutoSaveFile(self, baseName=''):
        """Remove the backup auto save file if it exists"""
        filePath = self.autoSaveFilePath(baseName)
        if filePath:
            try:
                os.remove(filePath)
            except OSError:
                print 'Could not remove backup file %s' % \
                      filePath.encode(globalref.localTextEncoding)

    def restoreAutoSaveFile(self, baseName):
        """Open backup file, then move baseName~ to baseName by overwriting,
           return True on success"""
        fileName = baseName + '~'
        self.openFile(fileName, False, False)
        if globalref.docRef.fileName != fileName:
            return False
        try:
            os.remove(baseName)
        except OSError:
            print 'Could not remove file %s' % \
                  baseName.encode(globalref.localTextEncoding)
            return False
        try:
            os.rename(fileName, baseName)
        except OSError:
            print 'Could not rename file %s' % \
                  fileName.encode(globalref.localTextEncoding)
            return False
        globalref.docRef.fileName = baseName
        globalref.mainWin.setMainCaption()
        return True

    def savePrompt(self, closing=False):
        """Ask for save if doc modified, return false on cancel"""
        win = globalref.mainWin
        if not self.duplicateWindows():
            if win.doc.modified and (closing or not globalref.options.
                                     boolData('OpenNewWindow')):
                text = win.fileImported and _('Save changes?') or \
                       _('Save changes to "%s"?') % win.doc.fileName
                ans = QtGui.QMessageBox.information(win, 'TreeLine', text,
                                                    _('&Yes'), _('&No'),
                                                    _('&Cancel'), 0, 2)
                if ans == 0:
                    self.fileSave()
                elif ans == 1:
                    self.delAutoSaveFile()
                    return True
                else:
                    return False
            if globalref.options.boolData('PersistTreeState'):
                self.recentFiles.saveTreeState(win.treeView)
        return True

    def duplicateWindows(self):
        """Return list of windows with the same file as the active window"""
        return [win for win in self.windowList if win != globalref.mainWin and
                win.doc.fileName == globalref.mainWin.doc.fileName]

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
