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
from time import sleep

import pyworkflow.object
from pyworkflow.protocol import ProtStreamingBase, params
from pyworkflow.utils import Message, removeBaseExt, redStr, greenStr, isFileFinished, strToDuration
from pwem.objects import SetOfImages, Image, ImageDim

CORRECTED_IMAGES = "correctedImages"

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

        form.addParam('fileAge', params.StringParam,
                      label='File finished after',
                      allowsNull=False,
                      default="7h",
                      help="File will be considered finished if it has not been modified for this time. %s" % HELP_DURATION_FORMAT)

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
            for folder in self.findProcessingFolders(self.images.get()):

                for file in os.listdir(folder):

                    file = os.path.join(folder,file)
                    self.debug("%s file is in process folder." % file)

                    if not self.fileDone(file):

                        # If file is finished
                        if isFileFinished(file, strToDuration(self.fileAge.get())):
                            beadsFile = self.getBeadsFile(file)

                            if beadsFile:

                                # Get the last modification time

                                self._insertFunctionStep(self.correctStep, file, beadsFile, prerequisites=[])
                                self.info(greenStr("New file %s detected. Adding it for correction." % file))
                            else:
                                self.info(redStr("No beads file found for %s. Skipping it." % file))
                        else:
                            self.debug("File %s is not finished. It has changed in the last %s." %(file, self.fileAge.get()))
            now = datetime.datetime.now()

            secsToWait = strToDuration(self.waitingTime.get())

            nextCheck = now + datetime.timedelta(seconds=secsToWait)

            self.info("Sleeping now. Next check will be at %s" % nextCheck.strftime("%A %H:%M"))
            sleep(secsToWait)

            keepchecking = True

    def findProcessingFolders(self, folder):
        """ Iterates over all the folders and subfolders looking for Beads file.
        Stops the search in depth when a folder with beads file is found. Search is recursive."""

        subfolders = []

        for file in os.listdir(folder):
            file = os.path.join(folder,file)
            if os.path.isdir(file):
              subfolders.append(file)
            # If file is a Beads file
            elif self.isBeadsFile(file):
                yield folder
                return

        # If codes reaches this part it is not a Processing folder
        for folder in subfolders:
            yield from self.findProcessingFolders(folder)

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
            self.debug("Is %s a beads file?." % sameFolderFile)
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

        outputFolder = os.path.dirname(file)
        args = '--ij2 --headless --default-gc'
        args += ' --run "%s"' % os.path.join(self.getPlugin().getPluginDir(),"scripts", "bUnwarpJ_code.groovy")
        args += ' "inputFile=\'%s\',beadsFile=\'%s\',outputDir=\'%s\',fixedCh=%s,headless=true"' % \
                (file, beadsFile, outputFolder , self.refChannel.get())

        self.runJob(self.getPlugin().getFijiLauncher(), args)


        # Register the output. Output is in a folder names like the base name fo the file
        outputFolderName = removeBaseExt(file)
        outputFolder = os.path.join(outputFolder, outputFolderName)
        output = self.getOutputSet()

        # I assume it is a 2 level folder structure: output folder>series folder>tif files.
        for outputFile in os.listdir(outputFolder):
            seriesFolder= os.path.join(outputFolder, outputFile)
            if os.path.isdir(seriesFolder):
                newCorrectedImage = None
                for index, tifFile in enumerate(os.listdir(seriesFolder)):
                    tifFile= os.path.join(seriesFolder, tifFile)
                    if index==0:
                        newCorrectedImage = Image(location=tifFile)
                    elif index in [1,2]:
                        setattr(newCorrectedImage,"image"+str(index), pyworkflow.object.String(tifFile))
                    else:
                        self.info("Unexpected extra image found: %s" % tifFile)
                output.append(newCorrectedImage)
            else:
                self.info("%s is a file: This was not expected." % seriesFolder)

        output.write()
        self._store()

    def getOutputSet(self):

        if not hasattr(self, CORRECTED_IMAGES):

            output = SetOfImages.create(self.getPath())
            output.setSamplingRate(1)

            self._defineOutputs(**{CORRECTED_IMAGES:output})
        else:
            output = getattr(self, CORRECTED_IMAGES)
            output.enableAppend()

        return output




    # --------------------------Helper functions ----------------------------------


    # --------------------------- INFO functions -----------------------------------
    def _summary(self):
        """ Summarize what the protocol has done"""
        return []

    def _methods(self):
        return []
