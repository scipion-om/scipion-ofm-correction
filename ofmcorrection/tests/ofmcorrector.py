import os
import pathlib

from pyworkflow.tests import BaseTest
from ofmcorrection.protocols import ofmcorrCorrector
import shutil

class TestOFM(BaseTest):
    def test_findProcessingFolders(self):

        corrector = ofmcorrCorrector()

        shutil.rmtree('/tmp/ofmroot', ignore_errors=True)

        os.mkdir("/tmp/ofmroot")
        os.mkdir("/tmp/ofmroot/folder1")
        os.mkdir("/tmp/ofmroot/folder1/folder11")
        pathlib.Path("/tmp/ofmroot/folder1/folder11/Beads.lif").touch()

        os.mkdir("/tmp/ofmroot/folder2")
        pathlib.Path("/tmp/ofmroot/folder2/Beads.lif").touch()

        folders = []

        for folder in corrector.findProcessingFolders("/tmp/ofmroot"):
            folders.append(folder)

        print(folders)
        self.assertTrue("/tmp/ofmroot/folder2" in folders, "Folder 2 not returned")

        self.assertTrue("/tmp/ofmroot/folder1/folder11" in folders, "Folder 11 not returned")

