# -*- coding: utf-8 -*-
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
# *  e-mail address 'pconesa@cnb.csic.es'
# *
# **************************************************************************


"""
Describe your python module here:
This module will provide the traditional Hello world example
"""
import datetime
import os
from glob import glob
from time import sleep

from ofmcorrection import Plugin
from pyworkflow.protocol import ProtStreamingBase, params, STEPS_PARALLEL
from pyworkflow.utils import Message, removeBaseExt, redStr

HELP_DURATION_FORMAT = "Duration format example: 1d 20h 30m 30s --> 1 day 20 hours 30 minutes and 30 seconds"
class ofmcorrCorrector(ProtStreamingBase):
    """
    Corrects optical fluorecence microscopy images/channels based on calibration images
    """
    _label = 'OFM Corrector'
    _handledFiles = [] # To store files detected that have been dealt with and have a step for them


    # -------------------------- DEFINE param functions ----------------------
    def _defineParams(self, form):
        """ Define the input parameters that will be used.
        Params:
            form: this is the form to be populated with sections and params.
        """
        # You need a params to belong to a section:
        form.addSection(label=Message.LABEL_INPUT)
        form.addParam('beadsFile', params.StringParam,
                      label='Beads file pattern', important=False,
                      default="Beads",
                      allowsNull=False,
                      help='Pattern of the beads file name. Must contain this text.')

        form.addParam('images', params.FileParam,
                      label='OFM Root folder', important=False,
                      allowsNull=False,
                      help='Path to the OFM sample images')

        form.addParam('refChannel', params.IntParam,
                      default=0,
                      label='Fixed/Target channel',
                      help='Channel number in the images file to be use as the reference.')

        form.addParam('waitingTime', params.StringParam,
                      default="1d",
                      label='Scanning waiting time',
                      help='Time to wait for the next folder scan. %s' % HELP_DURATION_FORMAT)

        form.addParallelSection(threads=3, mpi=1)

    # --------------------------- STEPS functions ------------------------------


    def stepsGeneratorStep(self):

        """ Checks if new input is available for processing"""

        keepchecking = True
        while keepchecking:

            # Look up in the input images folder
            # Glob HERE.

            for file in glob(self.images.get()):

                # Exclude Beads file...
                self.info("%s file listed." % file)


                if not self.fileDone(file):
                    beadsFile = self.getBeadsFile(file)

                    if beadsFile:
                        self._insertFunctionStep(self.correctStep, file, beadsFile, prerequisites=[])
                        self.info("New file %s detected. Adding it for correction."  % file)
                    else:
                        self.info("No beads file found for %s. Skipping it." % file)

            now = datetime.datetime.now()

            secsToWait = self.durationStr2Seconds(self.waitingTime.get())

            nextCheck = now + datetime.timedelta(seconds=secsToWait)

            self.info("Sleeping now. Next check will be at %s" % nextCheck )
            sleep(secsToWait)

            keepchecking = True

    def fileDone(self, file):
        """ Checks if the file has been processed already"""

        if file in self._handledFiles:
            self.debug("File %s already handled." % file)
            return True
        else:
            # Output exist form a previous execution (continuing mode) or
            # is new. In any case we annotate it as done to be skip next time
            self._handledFiles.append(file)

            outputFolder = self.getOutputFolder(file)
            exists= os.path.exists(outputFolder)

            if exists:
                self.debug("File %s already processed. It's output folder (%s) exists." % (file, outputFolder))

            return exists

    def getOutputFolder(self, file):
        """ Returns the output folder where the processing output will be stored"""

        # Base name
        bn = removeBaseExt(file)
        folder = os.path.dirname(file)
        return os.path.join(folder, bn)

    def getBeadsFile(self, file):
        """ Beads file is in the same folder as the image file matching  the beads pattern"""

        folder = os.path.dirname(file)

        for sameFolderFile in os.listdir(folder):
            self.info("Is %s a beads file?." % sameFolderFile)
            if self.isBeadsFile(sameFolderFile):

                beadsFile = os.path.join(folder, sameFolderFile)
                self.info("Beads file for %s found: %s" % (file, beadsFile))
                return beadsFile

    def isBeadsFile(self, file):
        """ Returns true if the file matches the beads file pattern"""
        return self.beadsFile.get() in file

    def correctStep(self, file, beadsFile):
        """ Runs the correction command in imageJ

        Example taken from https://github.com/acayuelalopez/bUnwarpJ_code

        /path/to/ImageJ-linux64
            --ij2
            --headless
            --run "/path/to/groovyscript/bUnwarpJ_Ana.groovy"
            "inputFilesDir='/path/to/inputFiles/images',beadsFile='/path/to/beadsFile/Sylvia Gutierrez-Erlandsson - Beads ref.lif - Image001.tif',outputDir='/path/to/outputFolder/results',fixedCh=0,headless=true"
        """

        self.info("Correction step invoked.")

        if beadsFile is None:
            self.warning(redStr("Beads file not found for %s. Check beads file pattern  (%s) or that "
                                "the folder contains the beads file." % (file, self.beadsFile.get())))
            self._handledFiles.remove(file)
            return
        args = '--ij2 --headless --default-gc'
        args += ' --run "%s"' % os.path.join(Plugin.getPluginDir(),"scripts", "bUnwarpJ_code.groovy")
        args += ' "inputFile=\'%s\',beadsFile=\'%s\',outputDir=\'%s\',fixedCh=%s,headless=true"' % \
                (file, beadsFile, os.path.dirname(file) , self.refChannel.get())

        self.runJob(Plugin.getFijiLauncher(), args)


    # --------------------------Helper functions ----------------------------------
    def durationStr2Seconds(self, durationStr):
        """ parses a duration string like 1d 2h 20m into seconds and returns it"""

        toEval = durationStr.replace("d", "*3600*24")\
            .replace("h", "*3600")\
            .replace("m", "*60") \
            .replace("s", "") \
            .replace(" ", "+")
        return eval(toEval)


    # --------------------------- INFO functions -----------------------------------
    def _summary(self):
        """ Summarize what the protocol has done"""
        return []

    def _methods(self):
        return []
