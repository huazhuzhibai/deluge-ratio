#
# core.py
#
# Copyright (C) 2009 Jesse Johnson <holocronweaver>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
#       The Free Software Foundation, Inc.,
#       51 Franklin Street, Fifth Floor
#       Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

from deluge.log import LOG as log
from deluge.plugins.pluginbase import CorePluginBase
import deluge.component as component
import deluge.configmanager
from deluge.core.rpcserver import export

from twisted.internet.task import LoopingCall

DEFAULT_PREFS = {
    'persistent': True,
    'total_download': 0,
    'total_upload': 0
}

class Core(CorePluginBase):
    enabled = False

    def enable(self):
        if self.enabled: return
        else: enabled = True

        self.config = deluge.configmanager.ConfigManager(
            "ratio.conf", DEFAULT_PREFS)

        if self.config['persistent']:
            log.info('Restoring ratio values')
            self.prev_session_total_download = self.config['total_download']
            self.prev_session_total_upload = self.config['total_upload']
            self.total_download = self.config['total_download']
            self.total_upload = self.config['total_upload']
        else:
            self.prev_session_total_download = 0
            self.prev_session_total_upload = 0
            self.total_download = 0
            self.total_upload = 0

        # Periodically update totals and ratio for GUI.
        self.update_timer = LoopingCall(self.update)
        self.update_timer.start(1)

        # Avoid losing ratio data if Deluge crashes.
        self.periodic_update_config_timer = LoopingCall(self.update_config)
        self.periodic_update_config_timer.start(63)

    def disable(self):
        self.update_timer.stop()
        self.periodic_update_config_timer.stop()
        self.update_config()

    def update(self):
        # Status comes from libtorrent session data, and is thus only
        # for this session.
        session = component.get('Core').get_session_status(
            ['total_download', 'total_upload'])

        self.total_download = self.prev_session_total_download + session['total_download']
        self.total_upload = self.prev_session_total_upload + session['total_upload']

    def update_config(self):
        log.debug('Updating Ratio plugin config with current totals.')
        if self.config['persistent']:
            self.config['total_download'] = self.total_download
            self.config['total_upload'] = self.total_upload
        self.config.save()

    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        for key in config.keys():
            self.config[key] = config[key]
        self.config.save()

    @export
    def get_config(self):
        """Returns the config dictionary"""
        return self.config.config

    @export
    def get_ratio_and_totals(self):
        ratio = 0
        if self.total_download > 0:
            ratio = float(self.total_upload) / self.total_download
        if self.total_upload < 2.0**40:
            return (ratio,
                self.total_upload / 2.0**30, self.total_download / 2.0**30, 'GiB')
        else:
            return (ratio,
                self.total_upload / 2.0**40, self.total_download / 2.0**40, 'TiB')

    @export
    def reset_ratio(self):
        """Resets the download and upload values, resetting the ratio."""
        self.total_download = 0
        self.total_upload = 0
        self.update_config()
