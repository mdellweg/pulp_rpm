# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
import shutil

from pulp.common.download.listener import DownloadEventListener

from pulp_rpm.common import models

_LOGGER = logging.getLogger(__name__)


class Listener(DownloadEventListener):
    def __init__(self, sync_conduit, success_callback, failure_callback):
        super(Listener, self).__init__()
        self.sync_conduit = sync_conduit
        self.success_callback = success_callback
        self.failure_callback = failure_callback

    def download_succeeded(self, report):
        """

        :param report:
        :type  report: pulp.common.download.report.DownloadReport
        :return:
        """
        model = models.from_package_info(report.data)
        # init unit, which is idempotent
        unit = self.sync_conduit.init_unit(model.TYPE, model.unit_key, model.metadata, model.relative_path)
        # move to final location
        shutil.move(report.destination, unit.storage_path)
        # save unit
        self.sync_conduit.save_unit(unit)
        self.success_callback(model)

    def download_failed(self, report):
        """

        :param report:
        :type  report: pulp.common.download.report.DownloadReport
        :return:
        """
        model = models.from_package_info(report.data)
        self.failure_callback(model, report.error_report)
