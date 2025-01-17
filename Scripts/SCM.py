﻿# ---------------------------------------------------------------------------
# |  
# |  SCM.py
# |  
# |  David Brownell (db@DavidBrownell.com)
# |  
# |  09/05/2015 10:02:02 AM
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
Tools for use with SourceControlManagement.
"""

import hashlib
import os
import re
import sys
import textwrap
import threading

from collections import OrderedDict
from six.moves import StringIO

import inflect
import six

from CommonEnvironment import ModifiableValue
from CommonEnvironment import CommandLine
from CommonEnvironment import FileSystem
from CommonEnvironment import Interface
from CommonEnvironment.QuickObject import QuickObject
from CommonEnvironment import Shell
from CommonEnvironment import six_plus
from CommonEnvironment import SourceControlManagement as SCMMod
from CommonEnvironment.StreamDecorator import StreamDecorator
from CommonEnvironment import TaskPool

# ---------------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ---------------------------------------------------------------------------

_SCMTypeInfo = CommandLine.EnumTypeInfo([ scm.Name for scm in SCMMod.GetPotentialSCMs() ])
_SCMOptionalTypeInfo = CommandLine.EnumTypeInfo(_SCMTypeInfo.Values, arity='?')

inflect_engine = inflect.engine()

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
def CommandLineSuffix():
    return textwrap.dedent(
        """
            The SCM will be auto-detected if not specified. If specified, it can be one 
            of the following values:
        
        {values}

        """).format( values='\n'.join([ "        - {}".format(scm_name) for scm_name in _SCMTypeInfo.Values ]),
                   )

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def Info( directory=None,
          output_stream=sys.stdout,
        ):
    directory = directory or os.getcwd()

    col_widths = [ 60, 12, 9, ]
    template = "{name:<%d}  {is_available:<%d}  {is_active:<%d}\n" % tuple(col_widths)

    output_stream.write(template.format( name="Name",
                                         is_available="Is Available",
                                         is_active="Is Active",
                                       ))
    output_stream.write(template.format( name='-' * col_widths[0],
                                         is_available='-' * col_widths[1],
                                         is_active='-' * col_widths[2],
                                       ))

    for scm in SCMMod.GetPotentialSCMs():
        is_available = scm.IsAvailable()

        output_stream.write(template.format( name=scm.Name,
                                             is_available="True" if is_available else "False",
                                             is_active="True" if is_available and scm.IsActive(directory) else "False",
                                           ))

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMTypeInfo,
                                  uri=CommandLine.StringTypeInfo(),
                                  output_directory=CommandLine.StringTypeInfo(),
                                  branch=CommandLine.StringTypeInfo(),
                                  output_stream=None,
                                )
def Clone( scm,
           uri,
           output_directory,
           branch=None,
           output_stream=sys.stdout,
         ):
    scm, _ = _GetSCMAndDir(scm, None)
    return CommandLine.DisplayOutput(*scm.Clone(uri, output_directory, branch or ''), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMTypeInfo,
                                  output_directory=CommandLine.StringTypeInfo(),
                                  output_stream=None,
                                )
def Create( scm,
            output_directory,
            output_stream=sys.stdout,
          ):
    scm, _ = _GetSCMAndDir(scm, None)
    return CommandLine.DisplayOutput(*scm.Create(output_directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def GetRoot( scm=None,
             directory=None,
             output_stream=sys.stdout,
           ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(0, scm.GetRoot(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def GetUniqueName( scm=None,
                   directory=None,
                   output_stream=sys.stdout,
                 ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(0, scm.GetUniqueName(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def Who( scm=None,
         directory=None,
         output_stream=sys.stdout,
       ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(0, scm.Who(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def GetBranches( scm=None,
                 directory=None,
                 output_stream=sys.stdout,
               ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(0, scm.GetBranches(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def GetCurrentBranch( scm=None,
                      directory=None,
                      output_stream=sys.stdout,
                    ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(0, scm.GetCurrentBranch(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def GetCurrentNormalizedBranch( scm=None,
                                directory=None,
                                output_stream=sys.stdout,
                              ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(0, scm.GetCurrentNormalizedBranch(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def GetMostRecentBranch( scm=None,
                         directory=None,
                         output_stream=sys.stdout,
                       ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(0, scm.GetMostRecentBranch(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( branch=CommandLine.StringTypeInfo(),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def CreateBranch( branch,
                  scm=None,
                  directory=None,
                  output_stream=sys.stdout,
                ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(*scm.CreateBranch(directory, branch), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( branch=CommandLine.StringTypeInfo(),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def SetBranch( branch,
               scm=None,
               directory=None,
               output_stream=sys.stdout,
             ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(*scm.SetBranch(directory, branch), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( branch=CommandLine.StringTypeInfo(),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def SetBranchOrDefault( branch,
                        scm=None,
                        directory=None,
                        output_stream=sys.stdout,
                      ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(*scm.SetBranchOrDefault(directory, branch), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( revision=CommandLine.StringTypeInfo(),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def GetRevisionInfo( revision,
                     scm=None,
                     directory=None,
                     output_stream=sys.stdout,
                   ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(0, scm.GetRevisionInfo(directory, revision), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( file=CommandLine.FilenameTypeInfo(arity='*'),
                                  recurse=CommandLine.BoolTypeInfo(arity='?'),
                                  include_re=CommandLine.StringTypeInfo(arity='*'),
                                  exclude_re=CommandLine.StringTypeInfo(arity='*'),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def AddFiles( file=None,
              recurse=None,
              include_re=None,
              exclude_re=None,
              scm=None,
              directory=None,
              output_stream=sys.stdout,
            ):
    if recurse == None and (include_re or exclude_re):
        recurse = False

    if file != [] and recurse != None:
        raise CommandLine.UsageException("'file' or 'recurse' arguments may be provied, but not both at the same time")

    if file == [] and recurse == None:
        raise CommandLine.UsageException("'file' or 'recurse' must be provided.")

    if recurse != None and (include_re or exclude_re):
        include_re = [ re.compile(ire) for ire in (include_re or []) ]
        exclude_re = [ re.compile(ere) for ere in (exclude_re or []) ]

        # ---------------------------------------------------------------------------
        def Functor(fullpath):
            return ( (not exclude_re or not any(ere.match(fullpath) for ere in exclude_re)) and
                     (not include_re or any(ire.match(fullpath) for ire in include_re))
                   )

        # ---------------------------------------------------------------------------
    else:
        # ---------------------------------------------------------------------------
        def Functor(_):
            return True
        # ---------------------------------------------------------------------------
        
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(*scm.AddFiles(directory, file or recurse, functor=Functor), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def Clean( scm=None,
           directory=None,
           no_prompt=False,
           output_stream=sys.stdout,
         ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(*scm.Clean(directory, no_prompt=no_prompt), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def HasWorkingChanges( scm=None,
                       directory=None,
                       output_stream=sys.stdout,
                     ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(0, scm.HasWorkingChanges(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def HasUntrackedWorkingChanges( scm=None,
                                directory=None,
                                output_stream=sys.stdout,
                              ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(0, scm.HasUntrackedWorkingChanges(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def GetChangeStatus( scm=None,
                     directory=None,
                     output_stream=sys.stdout,
                   ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(0, scm.GetChangeStatus(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( patch_filename=CommandLine.StringTypeInfo(),
                                  start_change=CommandLine.StringTypeInfo(arity='?'),
                                  end_change=CommandLine.StringTypeInfo(arity='?'),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def CreatePatch( patch_filename,
                 start_change=None,
                 end_change=None,
                 scm=None,
                 directory=None,
                 output_stream=sys.stdout,
               ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(*scm.CreatePatch(directory, patch_filename, start_change=start_change, end_change=end_change), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( patch_filename=CommandLine.FilenameTypeInfo(),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def ApplyPatch( patch_filename,
                commit=False,
                scm=None,
                directory=None,
                output_stream=sys.stdout,
              ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(*scm.ApplyPatch(directory, patch_filename, commit=commit), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( description=CommandLine.StringTypeInfo(),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def Commit( description,
            scm=None,
            directory=None,
            output_stream=sys.stdout,
          ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(*scm.Commit(directory, description), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( revision=CommandLine.StringTypeInfo(arity='?'),
                                  branch=CommandLine.StringTypeInfo(arity='?'),
                                  date=CommandLine.DateTimeTypeInfo(arity='?'),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def Update( revision=None,
            branch=None,
            date=None,
            scm=None,
            directory=None,
            output_stream=sys.stdout,
          ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(*scm.Update(directory, SCMMod.UpdateMergeArg.FromCommandLine(revision, branch, date)), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( revision=CommandLine.StringTypeInfo(arity='?'),
                                  branch=CommandLine.StringTypeInfo(arity='?'),
                                  date=CommandLine.DateTimeTypeInfo(arity='?'),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def Merge( revision=None,
           branch=None,
           date=None,
           scm=None,
           directory=None,
           output_stream=sys.stdout,
         ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(*scm.Merge(directory, SCMMod.UpdateMergeArg.FromCommandLine(revision, branch, date)), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( dest_branch=CommandLine.StringTypeInfo(),
                                  source_revision=CommandLine.StringTypeInfo(arity='?'),
                                  source_branch=CommandLine.StringTypeInfo(arity='?'),
                                  source_date=CommandLine.DateTimeTypeInfo(arity='?'),
                                  source_date_greater=CommandLine.BoolTypeInfo(arity='?'),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def GetRevisionsSinceLastMerge( dest_branch,
                                source_revision=None,
                                source_branch=None,
                                source_date=None,
                                source_date_greater=None,
                                scm=None,
                                directory=None,
                                output_stream=sys.stdout,
                              ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput( 0, 
                                      scm.GetRevisionsSinceLastMerge( directory, 
                                                                      dest_branch, 
                                                                      SCMMod.UpdateMergeArg.FromCommandLine( source_revision, 
                                                                                                             source_branch, 
                                                                                                             source_date,
                                                                                                             date_greater=source_date_greater,
                                                                                                           ),
                                                                    ), 
                                      output_stream=output_stream,
                                    )

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( revision=CommandLine.StringTypeInfo(arity='?'),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def GetChangedFiles( revision=None,
                     scm=None,
                     directory=None,
                     output_stream=sys.stdout,
                   ):
    scm, directory = _GetSCMAndDir(scm, directory)
    return CommandLine.DisplayOutput(0, scm.GetChangedFiles(directory, revision), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( filename=CommandLine.FilenameTypeInfo(ensure_exists=False),
                                  scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def EnumBlameInfo( filename,
                   scm=None,
                   directory=None,
                   output_stream=sys.stdout,
                 ):
    scm, directory = _GetSCMAndDir(scm, directory)

    common_prefix = FileSystem.GetCommonPath(filename, directory)
    if not common_prefix:
        raise CommandLine.UsageException("'{}' must be within the repository root of '{}'.".format(filename, directory))

    return CommandLine.DisplayOutput(0, scm.EnumBlameInfo(directory, filename), output_stream=output_stream)

# ----------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def EnumTrackedFiles( scm=None,
                      directory=None,
                      no_display=False,
                      output_stream=sys.stdout,
                    ):
    scm, directory = _GetSCMAndDir(scm, directory)

    if no_display:
        output_filename = lambda filename: None
    else:
        output_filename = lambda filename: output_stream.write("{}\n".format(filename))

    num_filenmes = 0

    for filename in scm.EnumTrackedFiles(directory):
        output_filename(filename)
        num_filenmes += 1

    output_stream.write("\n{} files.\n".format(num_filenmes))

# ---------------------------------------------------------------------------
# |  Distributed SCM Methods

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def Reset( no_prompt=False,
           no_backup=False,
           scm=None,
           directory=None,
           output_stream=sys.stdout,
         ):
    scm, directory = _GetSCMAndDir(scm, directory)
    if not scm.IsDistributed:
        output_stream.write("'{}' is not a distributed source control management system, which is a requirement for this functionality.\n".format(scm.Name))
        return -1

    return CommandLine.DisplayOutput(*scm.Reset(directory, no_prompt=no_prompt, no_backup=no_backup), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def HasUpdateChanges( scm=None,
                      directory=None,
                      output_stream=sys.stdout,
                    ):
    scm, directory = _GetSCMAndDir(scm, directory)
    if not scm.IsDistributed:
        output_stream.write("'{}' is not a distributed source control management system, which is a requirement for this functionality.\n".format(scm.Name))
        return -1

    return CommandLine.DisplayOutput(0, scm.HasUpdateChanges(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def HasLocalChanges( scm=None,
                     directory=None,
                     output_stream=sys.stdout,
                   ):
    scm, directory = _GetSCMAndDir(scm, directory)
    if not scm.IsDistributed:
        output_stream.write("'{}' is not a distributed source control management system, which is a requirement for this functionality.\n".format(scm.Name))
        return -1

    return CommandLine.DisplayOutput(0, scm.HasLocalChanges(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def GetLocalChanges( scm=None,
                     directory=None,
                     output_stream=sys.stdout,
                   ):
    scm, directory = _GetSCMAndDir(scm, directory)
    if not scm.IsDistributed:
        output_stream.write("'{}' is not a distributed source control management system, which is a requirement for this functionality.\n".format(scm.Name))
        return -1

    return CommandLine.DisplayOutput(0, scm.GetLocalChanges(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def HasRemoteChanges( scm=None,
                      directory=None,
                      output_stream=sys.stdout,
                    ):
    scm, directory = _GetSCMAndDir(scm, directory)
    if not scm.IsDistributed:
        output_stream.write("'{}' is not a distributed source control management system, which is a requirement for this functionality.\n".format(scm.Name))
        return -1

    return CommandLine.DisplayOutput(0, scm.HasRemoteChanges(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def GetRemoteChanges( scm=None,
                      directory=None,
                      output_stream=sys.stdout,
                    ):
    scm, directory = _GetSCMAndDir(scm, directory)
    if not scm.IsDistributed:
        output_stream.write("'{}' is not a distributed source control management system, which is a requirement for this functionality.\n".format(scm.Name))
        return -1

    return CommandLine.DisplayOutput(0, scm.GetRemoteChanges(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def Push( create_remote_branch=False,
          scm=None,
          directory=None,
          output_stream=sys.stdout,
        ):
    scm, directory = _GetSCMAndDir(scm, directory)
    if not scm.IsDistributed:
        output_stream.write("'{}' is not a distributed source control management system, which is a requirement for this functionality.\n".format(scm.Name))
        return -1

    return CommandLine.DisplayOutput(*scm.Push(directory, create_remote_branch=create_remote_branch), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def Pull( scm=None,
          directory=None,
          output_stream=sys.stdout,
        ):
    scm, directory = _GetSCMAndDir(scm, directory)
    if not scm.IsDistributed:
        output_stream.write("'{}' is not a distributed source control management system, which is a requirement for this functionality.\n".format(scm.Name))
        return -1

    return CommandLine.DisplayOutput(*scm.Pull(directory), output_stream=output_stream)

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def PullAndUpdate( scm=None,
                   directory=None,
                   output_stream=sys.stdout,
                 ):
    scm, directory = _GetSCMAndDir(scm, directory)
    if not scm.IsDistributed:
        output_stream.write("'{}' is not a distributed source control management system, which is a requirement for this functionality.\n".format(scm.Name))
        return -1

    result = CommandLine.DisplayOutput(*scm.Pull(directory), output_stream=output_stream)
    if result != 0:
        return result

    result = CommandLine.DisplayOutput(*scm.Update(directory, SCMMod.EmptyUpdateMergeArg()), output_stream=output_stream)
    if result != 0:
        return result

    return 0

# ----------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( scm=_SCMOptionalTypeInfo,
                                  directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def PruneDirectories( remove=False,
                      scm=None,
                      directory=None,
                      output_stream=sys.stdout,
                    ):
    scm, directory = _GetSCMAndDir(scm, directory)

    with StreamDecorator(output_stream).DoneManager( line_prefix='',
                                                     done_prefix="\nResults: ",
                                                     done_suffix='\n',
                                                   ) as dm:
        # ----------------------------------------------------------------------
        def CalculateHash(filename):
            hash = hashlib.sha512()

            hash.update(six_plus.StringToBytes(filename))
            return hash.hexdigest()

        # ----------------------------------------------------------------------
        class DirInfo(object):
            def __init__(self):
                self.children               = {}
                self.has_tracked            = False

        # ----------------------------------------------------------------------

        dm.stream.write("Processing tracked files...")

        num_files = ModifiableValue(0)
        with dm.stream.DoneManager( done_suffix_functor=lambda: "{} found".format(inflect_engine.no("file", num_files.value)),
                                  ) as this_dm:
            tracked = set()

            for filename in scm.EnumTrackedFiles(directory):
                num_files.value += 1
                
                tracked.add(CalculateHash(filename))

        dm.stream.write("Processing local files...")

        num_files = ModifiableValue(0)
        with dm.stream.DoneManager( done_suffix_functor=lambda: "{} found".format(inflect_engine.no("file", num_files.value)),
                                  ) as this_dm:
            all_dirs = DirInfo()

            for filename in FileSystem.WalkFiles(directory):
                num_files.value += 1

                # Add the file's ancestors to the dir structure
                dir_stack = [ all_dirs, ]

                for part in os.path.dirname(filename).split(os.path.sep):
                    if part not in dir_stack[0].children:
                        dir_stack[0].children[part] = DirInfo()

                    dir_stack.insert(0, dir_stack[0].children[part])

                # Is this a tracked file
                if CalculateHash(filename) in tracked:
                    for dir_info in dir_stack:
                        if dir_info.has_tracked:
                            break

                        dir_info.has_tracked = True
                
        dm.stream.write("Calculating differences...")
        
        to_remove = []
        with dm.stream.DoneManager( done_suffix_functor=lambda: "{} to remove".format(inflect_engine.no("directory", len(to_remove))),
                                  ) as this_dm:
            # ----------------------------------------------------------------------
            def Traverse(dir_info, name_parts):
                for k, v in six.iteritems(dir_info.children):
                    name_list = name_parts + [ k, ]

                    if v.has_tracked:
                        Traverse(v, name_list)
                    else:
                        to_remove.append(os.path.sep.join(name_list))

            # ----------------------------------------------------------------------

            Traverse(all_dirs, [])

        if remove:
            dm.stream.write("Removing directories...")
            with dm.stream.DoneManager() as this_dm:
                for index, directory in enumerate(to_remove):
                    this_dm.stream.write("Removing '{}' ({} of {})...".format( directory,
                                                                               index + 1,
                                                                               len(to_remove),
                                                                             ))
                    with this_dm.stream.DoneManager():
                        FileSystem.RemoveTree(directory)
        else:
            dm.stream.write(StreamDecorator.LeftJustify( textwrap.dedent(
                                                            """\

                                                            If '/remove' had been provided on the command line, the following directories
                                                            would have been removed:

                                                                {}

                                                            """).format(StreamDecorator.LeftJustify( '\n'.join(to_remove),
                                                                                                     4,
                                                                                                   )),
                                                         4,
                                                       ))
       
        return dm.result

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def AllChangeStatus( directory=None,
                     output_stream=sys.stdout,
                   ):
    directory = directory or os.getcwd()

    changes = []
    changes_lock = threading.Lock()

    # ----------------------------------------------------------------------
    def Query(scm, directory, task_index):
        status = scm.GetChangeStatus(directory)
        if status:
            with changes_lock:
                if len(changes) <= task_index:
                    changes.extend([ None, ] * (task_index - len(changes) + 1))

            changes[task_index] = QuickObject( scm=scm,
                                               directory=directory,
                                               status=status,
                                               current_branch=scm.GetCurrentBranch(directory),
                                             )
    
        return None
    
    # ----------------------------------------------------------------------
    
    result = _AllImpl( directory,
                       output_stream,

                       Query,

                       # No Action Required
                       None,
                       None,
                       None,

                       require_distributed=False,
                     )

    if not changes:
        return 0

    # Display the output
    cols = [ 80, 17, 25, 25, 9, 7, 5, 6, 6, ]
    template = "{dir:<%d}  {scm:<%d}  {recent_branch:<%d}  {working_branch:<%d}  {untracked:<%d}  {working:<%d}  {local:<%d}  {remote:<%d}  {update:<%d}" % tuple(cols)
    
    output_stream.write(textwrap.dedent(
        """\
                                                                                                                                    Branches                                         Changes
                                                                                                              /---------------------^^^^^^^^--------------------\\  /-----------------^^^^^^^---------------\\

        {}
        {}
        """).format( template.format( dir="Directory",
                                      scm="SCM",
                                      recent_branch="Most Recent",
                                      working_branch="Current",
                                      untracked="Untracked",
                                      working="Working",
                                      local="Local",
                                      remote="Remote",
                                      update="Update",
                                    ),
                     template.format( dir='-' * cols[0],
                                      scm='-' * cols[1],
                                      recent_branch='-' * cols[2],
                                      working_branch='-' * cols[3],
                                      untracked='-' * cols[4],
                                      working='-' * cols[5],
                                      local='-' * cols[6],
                                      remote='-' * cols[7],
                                      update='-' * cols[8],
                                    ),
                   ))

    for change in changes:
        if changes == None:
            continue

        output_stream.write("{}\n".format(template.format( dir=change.directory,
                                                           scm=change.scm.Name,
                                                           recent_branch=change.status.branch,
                                                           working_branch=change.current_branch,
                                                           untracked=str(change.status.untracked) if change.status.untracked != None else "N/A",
                                                           working=str(change.status.working),
                                                           local=str(change.status.local) if hasattr(change.status, "local") else "N/A",
                                                           remote=str(change.status.remote) if hasattr(change.status, "remote") else "N/A",
                                                           update=str(change.status.update) if hasattr(change.status, "update") else "N/A",
                                                         )))

    return 0

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def AllWorkingChangeStatus( directory=None,
                            output_stream=sys.stdout,
                          ):
    directory = directory or os.getcwd()

    changed_repos = []
    changed_repos_lock = threading.Lock()

    # ---------------------------------------------------------------------------
    def Query(scm, directory, task_index):
        result = scm.HasWorkingChanges(directory) or scm.HasUntrackedWorkingChanges(directory)
        if result:
            with changed_repos_lock:
                if len(changed_repos) <= task_index:
                    changed_repos.extend([ None, ] * (task_index - len(changed_repos) + 1))

            changed_repos[task_index] = (scm, directory)

        return result

    # ---------------------------------------------------------------------------
    
    result = _AllImpl( directory,
                       output_stream,
               
                       Query,
               
                       # No Action required
                       None,
                       None,
                       None,
               
                       require_distributed=True,
                     )
    if result != 0:
        return result

    changed_repos = [ cr for cr in changed_repos if cr ]
    
    if changed_repos:
        output_stream.write(textwrap.dedent(
            """\
            
            There are working changes in {}:
            {}
            
            """).format( inflect_engine.no("repository", len(changed_repos)),
                         '\n'.join([ "    - {}".format(directory) for scm, directory in changed_repos ]),
                       ))

    return 0

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def UpdateAll( directory=None,
               output_stream=sys.stdout,
             ):
    return _AllImpl( directory,
                     output_stream,

                     lambda scm, directory: not scm.IsDistributed or scm.HasUpdateChanges(directory),

                     "{dir} [{scm}] <Update>",
                     "Updating '{dir}'",
                     lambda scm, directory: scm.Update(directory, SCMMod.EmptyUpdateMergeArg()),

                     require_distributed=False,
                   )

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def PushAll( directory=None,
             output_stream=sys.stdout,
           ):
    return _AllImpl( directory,
                     output_stream,

                     lambda scm, directory: scm.HasLocalChanges(directory),

                     "{dir} [{scm}] <Push>",
                     "Pushing '{dir}'",
                     lambda scm, directory: scm.Push(directory),

                     require_distributed=True,
                   )

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def PullAll( directory=None,
             output_stream=sys.stdout,
           ):
    return _AllImpl( directory,
                     output_stream,

                     lambda scm, directory: scm.HasRemoteChanges(directory),

                     "{dir} [{scm}] <Pull>",
                     "Pulling '{dir}'",
                     lambda scm, directory: scm.Pull(directory),

                     require_distributed=True,
                   )

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( directory=CommandLine.DirectoryTypeInfo(arity='?'),
                                  output_stream=None,
                                )
def PullAndUpdateAll( directory=None,
                      output_stream=sys.stdout,
                    ):
    # ---------------------------------------------------------------------------
    def Action(scm, directory):

        sink = StringIO()

        for action in [ scm.Pull,
                        lambda d: scm.Update(d, SCMMod.EmptyUpdateMergeArg()),
                      ]:
            result, output = action(directory)
            sink.write(output)

            if result != 0:
                break

            sink.write('\n')

        return result, sink.getvalue().rstrip()

    # ---------------------------------------------------------------------------
    
    return _AllImpl( directory,
                     output_stream,

                     lambda scm, directory: scm.HasRemoteChanges(directory),

                     "{dir} [{scm}] <Pull and Update>",
                     "Pulling/Updating '{dir}'",
                     Action,

                     require_distributed=True,
                   )

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
def _GetSCMAndDir(scm_or_none, dir_or_none):
    dir_or_none = dir_or_none or os.getcwd()

    if scm_or_none:
        for scm in SCMMod.GetPotentialSCMs():
            if scm.Name == scm_or_none:
                return scm, dir_or_none

    scm = SCMMod.GetSCM(dir_or_none)
    if scm:
        dir_or_none = scm.GetRoot(dir_or_none)

    return scm, dir_or_none

# ---------------------------------------------------------------------------
def _GetSCMAndDirs(environment, root_dir):
    scm = SCMMod.GetSCM(root_dir, throw_on_error=False)
    if scm:
        if environment.IsSymLink(root_dir):
            root_dir = environment.ResolveSymLink(root_dir)

        yield scm, root_dir
        return

    for item in os.listdir(root_dir):
        fullpath = os.path.join(root_dir, item)
        if os.path.isdir(fullpath):
            if item in [ "Generated", ]:
                continue

            for result in _GetSCMAndDirs(environment, fullpath):
                yield result

# ---------------------------------------------------------------------------
# <Too many local variables> pylint: disable = R0914
def _AllImpl( directory,
              output_stream,
              
              query_func,                   # def Func(scm, directory) -> Bool

              action_name_template,
              action_status_template,
              action_func,                  # def Func(scm, directory) -> (result, output)

              require_distributed,
            ):
    directory = directory or os.getcwd()
    query_func = Interface.CreateCulledCallable(query_func)

    with StreamDecorator(output_stream).DoneManager( line_prefix='',
                                                     done_prefix="\nComposite Results: ",
                                                   ) as si:
        environment = Shell.GetEnvironment()

        items = []

        si.stream.write("\nSearching for repositories in '{}'...".format(directory))
        with si.stream.DoneManager( done_suffix_functor=lambda: "{} found".format(inflect_engine.no("repository", len(items))),
                                  ):
            items.extend(_GetSCMAndDirs(environment, directory))

        if not items:
            return 0

        output = [ None, ] * len(items)

        to_process = ModifiableValue(0)
        to_process_lock = threading.Lock()

        # ---------------------------------------------------------------------------
        def QueryProcess(scm, directory, task_index, task_output_stream, on_status_update):
            on_status_update("Querying")

            if not require_distributed or scm.IsDistributed:
                result = query_func(OrderedDict([ ( "scm", scm, ),
                                                  ( "directory", directory ),
                                                  ( "task_index", task_index ),
                                                ]))

                if result:
                    with to_process_lock:
                        to_process.value += 1

                output[task_index] = QuickObject( scm=scm,
                                                  directory=directory,
                                                  result=result,
                                                )

        # ---------------------------------------------------------------------------
        
        with si.stream.SingleLineDoneManager( "Processing {}...".format(inflect_engine.no("repository", len(items))),
                                              done_suffix_functor=None if not action_func else (lambda: "{} to execute".format(inflect_engine.no("repository", to_process.value))),
                                            ) as this_dm:
            TaskPool.Execute( [ TaskPool.Task(  "{} [{}] <Query>".format(directory, scm.Name),
                                                "Querying '{}'".format(directory),
                                                lambda task_index, task_output_stream, on_status_update, scm=scm, directory=directory: QueryProcess(scm, directory, task_index, task_output_stream, on_status_update),
                                             )
                                for scm, directory in items
                              ],
                              output_stream=this_dm.stream,
                              progress_bar=True,
                              # num_concurrent_tasks=1,
                            )

        action_items = [ data for data in output if data.result ]
        
        if action_func and action_items:
            # ----------------------------------------------------------------------
            def Invoke(action_item, task_index, output_stream, on_status_update):
                on_status_update("Executing")

                return action_func(action_item.scm, action_item.directory)

            # ----------------------------------------------------------------------
            
            tasks = []
            
            for action_item in action_items:
                template_args = { "dir" : action_item.directory,
                                  "scm" : action_item.scm.Name,
                                }
            
                tasks.append(TaskPool.Task( action_name_template.format(**template_args),
                                            action_status_template.format(**template_args),
                                            lambda task_index, output_stream, on_status_update, action_item=action_item: Invoke(action_item, task_index, output_stream, on_status_update),
                                          ))
            
            task_pool_result = TaskPool.Execute( tasks, 
                                                 output_stream=output_stream,
                                                 progress_bar=True,
                                                 verbose=True,
                                               )

            si.result = si.result or task_pool_result

        return si.result

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try: sys.exit(CommandLine.Main())
    except KeyboardInterrupt: pass
