﻿# ---------------------------------------------------------------------------
# |  
# |  NoopCodeCoverageExtractor.py
# |  
# |  David Brownell (db@DavidBrownell.com)
# |  
# |  09/20/2015 05:02:31 PM
# |  
# ---------------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2015-18.
# |          
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ---------------------------------------------------------------------------
"""\
<Used by other scripts>
"""

import os
import sys

from CommonEnvironment import CodeCoverageExtractor as CodeCoverageExtractorMod
from CommonEnvironment import Interface
from CommonEnvironment import Process
from CommonEnvironment.TimeDelta import TimeDelta

# ---------------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ---------------------------------------------------------------------------

@Interface.staticderived
class CodeCoverageExtractor(CodeCoverageExtractorMod.CodeCoverageExtractor):
    # ---------------------------------------------------------------------------
    # |  Public Properties
    Name                                    = "Noop"
    Description                             = "CodeCoverageExtractor that doesn't do anything but can be used when one is required."

    # ---------------------------------------------------------------------------
    # |  Public Methods
    @staticmethod
    def ValidateEnvironment():
        # No explicit environment requirements
        return

    # ---------------------------------------------------------------------------
    @staticmethod
    def IsSupportedCompiler(compiler):
        return True

    # ---------------------------------------------------------------------------
    @staticmethod
    def Execute( compiler,
                 context,
                 command_line,
                 includes=None,
                 excludes=None,
                 verbose=False,
               ):
        start_time = TimeDelta()

        results = CodeCoverageExtractorMod.Results()

        results.test_result, results.test_output = Process.Execute(command_line)
        
        results.test_duration = start_time.CalculateDelta(as_string=True)

        return results
