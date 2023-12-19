# **************************************************************************
# *
# * Authors:     Pablo Conesa (pconesa@cnb.csic.es)
# *
# * CNB - CSIC
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************

import pwem

_logo = "icon.png"
_references = ['you2019']

FIJI_LAUNCHER_VAR = 'FIJI_LAUNCHER'

class Plugin(pwem.Plugin):

    _homeVar = FIJI_LAUNCHER_VAR

    @classmethod
    def _defineVariables(cls):
        cls._defineVar(FIJI_LAUNCHER_VAR, '/home/pablo/software/Fiji-noJre.app/ImageJ-linux64')

    @classmethod
    def getFijiLauncher(cls):
        return cls.getVar(FIJI_LAUNCHER_VAR)