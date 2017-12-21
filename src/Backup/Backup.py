# ----------------------------------------------------------------------
# |  
# |  Backup.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2017-01-07 09:39:24
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2017.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
"""\
Processes files for offsite or mirrored backup.
"""

import hashlib
import itertools
import json
import os
import re
import shutil
import sys
import textwrap

from collections import OrderedDict

import inflect
import six
from six.moves import cPickle as pickle

from CommonEnvironment import Any, ModifiableValue
from CommonEnvironment.CallOnExit import CallOnExit
from CommonEnvironment import CommandLine
from CommonEnvironment import FileSystem
from CommonEnvironment import Process
from CommonEnvironment import Shell
from CommonEnvironment.StreamDecorator import StreamDecorator
from CommonEnvironment import TaskPool

# ----------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

inflect_engine                              = inflect.engine()

StreamDecorator.InitAnsiSequenceStreams()

# ----------------------------------------------------------------------
@CommandLine.EntryPoint( backup_name=CommandLine.EntryPoint.ArgumentInfo("Name used to uniquely identify the backup"),
                         output_dir=CommandLine.EntryPoint.ArgumentInfo("Output directory that will contain the compressed file(s)"),
                         input=CommandLine.EntryPoint.ArgumentInfo("One or more filenames or directories used to parse for input"),
                         force=CommandLine.EntryPoint.ArgumentInfo("Ignore previously saved information when calculating work to execute"),
                         use_links=CommandLine.EntryPoint.ArgumentInfo("Create symbolic links rather than copying files"),
                         auto_commit=CommandLine.EntryPoint.ArgumentInfo("Invoke 'CommitOffsite' automatically"),
                         include=CommandLine.EntryPoint.ArgumentInfo("One or more regular expressions used to specify filenames to include"),
                         exclude=CommandLine.EntryPoint.ArgumentInfo("One or more regular expressions used to specify filenames to exclude"),
                         traverse_include=CommandLine.EntryPoint.ArgumentInfo("One or more regular expressions used to specify directory names to include while parsing"),
                         traverse_exclude=CommandLine.EntryPoint.ArgumentInfo("One or more regular expressions used to specify directory names to exclude while parsing"),
                         display_only=CommandLine.EntryPoint.ArgumentInfo("Display the operations that would be taken but does not perform them"),
                       )
@CommandLine.FunctionConstraints( backup_name=CommandLine.StringTypeInfo(),
                                  output_dir=CommandLine.DirectoryTypeInfo(ensure_exists=False),
                                  input=CommandLine.FilenameTypeInfo(match_any=True, arity='+'),
                                  include=CommandLine.StringTypeInfo(arity='*'),
                                  exclude=CommandLine.StringTypeInfo(arity='*'),
                                  traverse_include=CommandLine.StringTypeInfo(arity='*'),
                                  traverse_exclude=CommandLine.StringTypeInfo(arity='*'),
                                  output_stream=None,
                                )
def Offsite( backup_name,
             output_dir,
             input,
             force=False,
             use_links=False,
             auto_commit=False,
             include=None,
             exclude=None,
             traverse_include=None,
             traverse_exclude=None,
             display_only=False,
             output_stream=sys.stdout,
             verbose=False,
             preserve_ansi_escape_sequences=False,
           ):
    """\
    Prepares data to backup based on the result of previous invocations.
    """
    
    inputs = input; del input
    includes = include; del include
    excludes = exclude; del exclude
    traverse_includes = traverse_include; del traverse_include
    traverse_excludes = traverse_exclude; del traverse_exclude

    with StreamDecorator.GenerateAnsiSequenceStream( output_stream,
                                                     preserve_ansi_escape_sequences=preserve_ansi_escape_sequences,
                                                   ) as output_stream:
        with output_stream.DoneManager( line_prefix='',
                                        done_prefix="\nResults: ",
                                        done_suffix='\n',
                                      ) as dm:
            environment = Shell.GetEnvironment()

            pickle_filename = _CreatePickleFilename(backup_name, environment)

            # Read the source info
            source_file_info = _GetFileInfo( "source",
                                             inputs,
                                             includes,
                                             excludes,
                                             traverse_includes,
                                             traverse_excludes,
                                             False,     # simple_compare
                                             dm.stream,
                                           )

            dm.stream.write('\n')

            # Read the destination info
            dest_file_info = {}
            dest_hashes = set()

            if not force and os.path.isfile(pickle_filename):
                try:
                    with open(pickle_filename, 'rb') as f:
                        dest_file_info = pickle.load(f)

                    for dfi in dest_file_info:
                        dest_hashes.add(dfi.Hash)

                except:
                    dm.stream.write("WARNING: The previously saved data appears to be corrupt and will not be used.\n")
            else:
                dest_file_info = {}

            # Calculate work to complete
            work = _CreateWork( source_file_info,
                                dest_file_info,
                                None,
                                False,     # simple_compare
                                dm.stream,
                                verbose,
                              )

            if display_only:
                _Display(work, dm.stream, show_dest=False)
                return dm.result

            # Process the files to add
            commands = []
            data = []
            
            if use_links:
                generate_command_func = lambda source, dest: environment.SymbolicLink(dest, source)
            else:
                generate_command_func = lambda source, dest: environment.CopyFile(source, dest)

            for sfi, dfi in six.iteritems(work):
                if sfi is None:
                    continue

                if sfi.Hash not in dest_hashes:
                    commands.append(generate_command_func(sfi.Name, os.path.join(output_dir, sfi.Hash)))
                    dest_hashes.add(sfi.Hash)

                data.append({ "filename" : sfi.Name,
                              "hash" : sfi.Hash,
                              "operation" : "add" if isinstance(dfi, six.string_types) else "modify",
                            })

            for dfi in work.get(None, []):
                data.append({ "filename" : dfi.Name,
                              "hash" : dfi.Hash,
                              "operation" : "remove",
                            })

            if not data:
                dm.stream.write("No content to apply.\n")
                dm.result = 1

                return dm.result

            dm.stream.write("Applying content...")
            with dm.stream.DoneManager( done_suffix='\n',
                                      ) as apply_dm:
                apply_dm.stream.write("Cleaning previous content...")
                with apply_dm.stream.DoneManager():
                    FileSystem.RemoveTree(output_dir)

                os.makedirs(output_dir)

                if commands:
                    apply_dm.stream.write("Creating content...")
                    with apply_dm.stream.DoneManager():
                        apply_dm.result, output = environment.ExecuteCommands(commands)
                        if apply_dm.result != 0:
                            apply_dm.stream.write(output)
                            return apply_dm.result

                with open(os.path.join(output_dir, "data.json"), 'w') as f:
                    json.dump(data, f)

            dm.stream.write("Writing pending data...")
            with dm.stream.DoneManager():
                pending_pickle_filename = _CreatePendingPickleFilename(pickle_filename)

                with open(pending_pickle_filename, 'wb') as f:
                    pickle.dump(source_file_info, f)

            if auto_commit:
                dm.result = CommitOffsite(backup_name, dm.stream)
            else:
                dm.stream.write(textwrap.dedent(
                    """\



                    ***** Pending data has been written, but will not be considered official until it is committed via a call to CommitOffsite. *****



                    """))

            return dm.result

# ----------------------------------------------------------------------
@CommandLine.EntryPoint( backup_name=CommandLine.EntryPoint.ArgumentInfo("Name used to uniquely identify the backup"),
                       )
@CommandLine.FunctionConstraints( backup_name=CommandLine.StringTypeInfo(),
                                  output_stream=None,
                                )
def CommitOffsite( backup_name,
                   output_stream=sys.stdout,
                   preserve_ansi_escape_sequences=False,
                 ):
    """\
    Commits data previously generated by Offsite. This can be useful when
    additional steps must be taken (for example, upload) before a Backup can 
    be considered as successful.
    """

    with StreamDecorator.GenerateAnsiSequenceStream( output_stream,
                                                     preserve_ansi_escape_sequences=preserve_ansi_escape_sequences,
                                                   ) as output_stream:
        with output_stream.DoneManager( line_prefix='',
                                        done_prefix="\nResults: ",
                                        done_suffix='\n',
                                      ) as dm:
            environment = Shell.GetEnvironment()

            pickle_filename = _CreatePickleFilename(backup_name, environment)
            pending_pickle_filename = _CreatePendingPickleFilename(pickle_filename)

            if not os.path.isfile(pending_pickle_filename):
                dm.stream.write("ERROR: Pending data was not found.\n")
                dm.result = -1
            else:
                FileSystem.RemoveFile(pickle_filename)
                shutil.move(pending_pickle_filename, pickle_filename)

                dm.stream.write("The pending data has been committed.\n")

            return dm.result

# ----------------------------------------------------------------------
@CommandLine.EntryPoint( destination=CommandLine.EntryPoint.ArgumentInfo("Destination directory"),
                         input=CommandLine.EntryPoint.ArgumentInfo("One or more filenames or directories used to parse for input"),
                         force=CommandLine.EntryPoint.ArgumentInfo("Ignore information in the destination when calculating work to execute"),
                         simple_compare=CommandLine.EntryPoint.ArgumentInfo("Compare via file size and modified date rather than with a hash. This will be faster, but more error prone when detecting changes."),
                         include=CommandLine.EntryPoint.ArgumentInfo("One or more regular expressions used to specify filenames to include"),
                         exclude=CommandLine.EntryPoint.ArgumentInfo("One or more regular expressions used to specify filenames to exclude"),
                         traverse_include=CommandLine.EntryPoint.ArgumentInfo("One or more regular expressions used to specify directory names to include while parsing"),
                         traverse_exclude=CommandLine.EntryPoint.ArgumentInfo("One or more regular expressions used to specify directory names to exclude while parsing"),
                         display_only=CommandLine.EntryPoint.ArgumentInfo("Display the operations that would be taken but do not perform them"),
                       )
@CommandLine.FunctionConstraints( destination=CommandLine.DirectoryTypeInfo(ensure_exists=False),
                                  input=CommandLine.FilenameTypeInfo(match_any=True, arity='+'),
                                  include=CommandLine.StringTypeInfo(arity='*'),
                                  exclude=CommandLine.StringTypeInfo(arity='*'),
                                  traverse_include=CommandLine.StringTypeInfo(arity='*'),
                                  traverse_exclude=CommandLine.StringTypeInfo(arity='*'),
                                  output_stream=None,
                                )
def Mirror( destination,
            input,
            force=False,
            simple_compare=False,
            include=None,
            exclude=None,
            traverse_include=None,
            traverse_exclude=None,
            display_only=False,
            output_stream=sys.stdout,
            verbose=False,
            preserve_ansi_escape_sequences=False,
          ):
    """\
    Mirrors files to a different location. Both the input source and destination are 
    scanned when calculating the operations necessary to ensure that the destination
    matches the input source(s).
    """

    destination = FileSystem.Normalize(destination)
    inputs = [ FileSystem.Normalize(i) for i in input ]; del input
    includes = include; del include
    excludes = exclude; del exclude
    traverse_includes = traverse_include; del traverse_include
    traverse_excludes = traverse_exclude; del traverse_exclude
        
    with StreamDecorator.GenerateAnsiSequenceStream( output_stream,
                                                     preserve_ansi_escape_sequences=preserve_ansi_escape_sequences,
                                                   ) as output_stream:
        with output_stream.DoneManager( line_prefix='',
                                        done_prefix="\nResults: ",
                                      ) as dm:
            source_file_info = _GetFileInfo( "source",
                                             inputs,
                                             includes,
                                             excludes,
                                             traverse_includes,
                                             traverse_excludes,
                                             simple_compare,
                                             dm.stream,
                                           )
            dm.stream.write("\n")
        
            if not force and os.path.isdir(destination):
                dest_file_info = _GetFileInfo( "destination",
                                               [ destination, ],
                                               None,
                                               None,
                                               None,
                                               None,
                                               simple_compare,
                                               dm.stream,
                                             )
        
                dm.stream.write("\n")
            else:
                dest_file_info = {}
        
            # Calculate the work to complete
            work = _CreateWork( source_file_info,
                                dest_file_info,
                                destination,
                                simple_compare,
                                dm.stream,
                                verbose,
                              )
        
            if display_only:
                _Display(work, dm.stream, show_dest=True)
                return dm.result

            if not os.path.isdir(destination):
                os.makedirs(destination)
            
            executed_work = False

            # Copy files
            tasks = []

            for sfi, dfi in six.iteritems(work):
                if sfi is None:
                    continue

                sfi = sfi.Name
                dfi = getattr(dfi, "Name", dfi)

                tasks.append((sfi, dfi))
                
            if tasks:
                # ----------------------------------------------------------------------
                def Execute(task_index, task_output):
                    try:
                        source, dest = tasks[task_index]

                        dest_dir = os.path.dirname(dest)
                        if not os.path.isdir(dest_dir):
                            os.makedirs(dest_dir)

                        shutil.copy2(source, dest)

                    except Exception as ex:
                        task_output.write(str(ex))
                        return -1

                # ----------------------------------------------------------------------

                with dm.stream.SingleLineDoneManager( "Copying {}...".format(inflect_engine.no("file", len(tasks))),
                                                    ) as this_dm:
                    this_dm.result = TaskPool.Execute( [ TaskPool.Task( "Copy '{}' to '{}'".format(source, dest),
                                                                        "Copying '{}' to '{}'".format(source, dest),
                                                                        Execute,
                                                                      )
                                                         for source, dest in tasks
                                                       ],
                                                       num_concurrent_tasks=1,
                                                       output_stream=this_dm.stream,
                                                       progress_bar=True,
                                                     )

                    if this_dm.result != 0:
                        return this_dm.result

                executed_work = True

            # Remove files
            remove_files = [ dfi.Name for dfi in work.get(None, []) ]
            if remove_files:
                # ----------------------------------------------------------------------
                def Execute(task_index, task_output):
                    try:
                        value = remove_files[task_index]
                        os.remove(value)

                    except Exception as ex:
                        task_output.write(str(ex))
                        return -1

                # ----------------------------------------------------------------------

                with dm.stream.SingleLineDoneManager( "Removing {}...".format(inflect_engine.no("file", len(remove_files))),
                                                    ) as this_dm:
                    this_dm.result = TaskPool.Execute( [ TaskPool.Task( "Remove '{}'".format(filename),
                                                                        "Removing '{}'".format(filename),
                                                                        Execute,
                                                                      )
                                                         for filename in remove_files
                                                       ],
                                                       num_concurrent_tasks=1,
                                                       output_stream=this_dm.stream,
                                                       progress_bar=True,
                                                     )

                    if this_dm.result != 0:
                        return this_dm.result

                executed_work = True

            if not executed_work:
                dm.result = 1

            return dm.result

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
class _FileInfo(object):
    # ----------------------------------------------------------------------
    def __init__( self, 
                  name,
                  size, 
                  last_modified, 
                  hash=None,
                ):
        self.Name                           = name
        self.Size                           = size
        self.LastModified                   = last_modified
        self.Hash                           = hash

    # ----------------------------------------------------------------------
    def __hash__(self):
        return hash(( self.Name, self.Size, self.LastModified, self.Hash, ))

    # ----------------------------------------------------------------------
    def __repr__(self):
        return "{}, {}, {}, {}".format( self.Name,
                                        self.Size, 
                                        self.LastModified, 
                                        self.Hash,
                                      )

    # ----------------------------------------------------------------------
    def AreEqual(self, other, compare_hashes=True):
        return ( self.Size == other.Size and
                 abs(self.LastModified - other.LastModified) <= 0.00001 and
                 (not compare_hashes or self.Hash == other.Hash)
               )

    # ----------------------------------------------------------------------
    def __eq__(self, other):
        return self.AreEqual(other)
            
    # ----------------------------------------------------------------------
    def __ne__(self, other):
        return not self.__eq__(other)

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
def _CreatePickleFilename(backup_name, environment):
    return environment.CreateDataFilename("{}.backup".format(backup_name))

# ----------------------------------------------------------------------
def _CreatePendingPickleFilename(pickle_filename):
    return "{}.pending".format(pickle_filename)

# ----------------------------------------------------------------------
def _GetFileInfo( desc,
                  inputs,
                  includes,
                  excludes,
                  traverse_includes,
                  traverse_excludes,
                  simple_compare,
                  output_stream,
                ):
    output_stream.write("Processing '{}'...".format(desc))
    with output_stream.DoneManager() as dm:
        input_files = []

        dm.stream.write("Processing content...")
        with dm.stream.DoneManager( done_suffix_functor=lambda: "{} found".format(inflect_engine.no("file", len(input_files))),
                                  ) as file_dm:
            input_dirs = []

            for i in inputs:
                if os.path.isfile(i):
                    input_files.append(i)
                elif os.path.isdir(i):
                    input_dirs.append(i)
                else:
                    raise CommandLine.UsageException("'{}' is not a valid file or directory".format(i))

            if input_dirs:
                file_dm.stream.write("Processing Directories...")
                with file_dm.stream.DoneManager() as dir_dm:
                    for index, input_dir in enumerate(input_dirs):
                        dir_dm.stream.write("'{}' ({} of {})...".format( input_dir,
                                                                         index + 1,
                                                                         len(input_dirs),
                                                                       ))
                        with dir_dm.stream.DoneManager():
                            input_files += FileSystem.WalkFiles( input_dir,
                                                                 traverse_include_dir_paths=traverse_includes,
                                                                 traverse_exclude_dir_paths=traverse_excludes,
                                                               )

        if includes or excludes:
            # ----------------------------------------------------------------------
            def ToRegexes(items):
                results = []

                for item in items:
                    try:
                        results.append(re.compile(item))
                    except:
                        raise CommandLine.UsageException("'{}' is not a valid regular expression".format(item))

                return results

            # ----------------------------------------------------------------------

            dm.stream.write("Filtering files...")
            with dm.stream.DoneManager( lambda: "{} to process".format(inflect_engine.no("file", len(input_files))),
                                      ):

                if includes:
                    include_regexes = ToRegexes(includes)
                    IncludeChecker = lambda input_file: Any(include_regexes, lambda regex: regex.match(input_file))
                else:
                    IncludeChecker = lambda input_file: True

                if excludes:
                    exclude_regexes = ToRegexes(excludes)
                    ExcludeChecker = lambda input_file: Any(exclude_regexes, lambda regex: regex.match(input_file))
                else:
                    ExcludeChecker = lambda input_file: False

                valid_files = []

                for input_file in input_files:
                    if not ExcludeChecker(input_file) and IncludeChecker(input_file):
                        valid_files.append(input_file)

                input_files[:] = valid_files

        file_info = []

        if input_files:
            with dm.stream.SingleLineDoneManager( "Calculating info...",
                                                ) as this_dm:
                # ----------------------------------------------------------------------
                def CalculateInfo(filename):
                    return _FileInfo( filename,
                                      os.path.getsize(filename),
                                      os.path.getmtime(filename),
                                    )

                # ----------------------------------------------------------------------
                def CalculateHash(filename):
                    info = CalculateInfo(filename)

                    sha = hashlib.sha224()

                    with open(filename, 'rb') as f:
                        while True:
                            data = f.read(8192)
                            if not data:
                                break

                            sha.update(data)

                    info.Hash = sha.hexdigest()

                    return info

                # ----------------------------------------------------------------------

                file_info += TaskPool.Transform( input_files,
                                                 CalculateInfo if simple_compare else CalculateHash,
                                                 this_dm.stream,
                                               )

        return file_info

# ----------------------------------------------------------------------
def _CreateWork( source_file_info,
                 dest_file_info,
                 optional_local_destination_dir,
                 simple_compare,
                 output_stream,
                 verbose,
               ):
    """\
    Returns a dict in the following format:

        - Added files will have a key that is _FileInfo (source) and value that is the destination filename
        - Modified files will have a key that is _FileInfo (source) and value that is _FileInfo (dest)
        - Removed files will have a key that is None and a value that is a list of _FileInfo (dest)
    """

    results = OrderedDict()

    output_stream.write("Processing file information...")
    with output_stream.DoneManager( done_suffix='\n',
                                  ) as dm:
        verbose_stream = StreamDecorator(dm.stream if verbose else None, "INFO: ")

        added = 0
        modified = 0
        removed = 0
        matched = 0

        source_map = { sfi.Name : sfi for sfi in source_file_info }
        dest_map = { dfi.Name : dfi for dfi in dest_file_info }

        ToDest, FromDest = _CreateFilenameMappingFunctions(source_file_info, optional_local_destination_dir)

        for sfi in six.itervalues(source_map):
            dest_filename = ToDest(sfi.Name)

            if dest_filename not in dest_map:
                verbose_stream.write("[Add] '{}' does not exist.\n".format(sfi.Name))

                results[sfi] = dest_filename
                added += 1
            elif sfi.AreEqual(dest_map[dest_filename]):
                matched += 1
            else:
                verbose_stream.write("[Modify] '{}' has changed.\n".format(sfi.Name))

                results[sfi] = dest_map[dest_filename]
                modified += 1

        for dfi in six.itervalues(dest_map):
            source_filename = FromDest(dfi.Name)
            
            if source_filename not in source_map:
                verbose_stream.write("[Remove] '{}' will be removed.\n".format(dfi.Name))

                results.setdefault(None, []).append(dfi)
                removed += 1

        total = added + modified + removed + matched

        dm.stream.write("- {0} to add ({1:.02f}%)\n".format( inflect_engine.no("file", added),
                                                             0.0 if total == 0 else (float(added) / total) * 100,
                                                           ))

        dm.stream.write("- {0} to modifiy ({1:.02f}%)\n".format( inflect_engine.no("file", modified),
                                                                 0.0 if total == 0 else (float(modified) / total) * 100,
                                                               ))
        dm.stream.write("- {0} to remove ({1:.02f}%)\n".format( inflect_engine.no("file", removed),
                                                                0.0 if total == 0 else (float(removed) / total) * 100,
                                                              ))
        dm.stream.write("- {0} matched ({1:.02f}%)\n".format( inflect_engine.no("file", matched),
                                                              0.0 if total == 0 else (float(matched) / total) * 100,
                                                            ))
    
    return results
        
# ----------------------------------------------------------------------
def _CreateFilenameMappingFunctions(source_file_info, optional_local_destination_dir):
    if optional_local_destination_dir is None:
        return lambda filename: filename, lambda filename: filename

    # ----------------------------------------------------------------------
    def IsMultiDrive():
        drive = None

        for file_info in source_file_info:
            this_drive = os.path.splitdrive(file_info.Name)[0]
            if this_drive != drive:
                if drive is None:
                    drive = this_drive
                else:
                    return True

        return False

    # ----------------------------------------------------------------------
        
    if IsMultiDrive():
        # ----------------------------------------------------------------------
        def ToDest(filename):
            drive, suffix = os.path.splitdrive(filename)
            drive = drive.replace(':', '_')

            suffix = FileSystem.RemoveInitialSep(suffix)
            
            return os.path.join(optional_local_destination_dir, drive, suffix)

        # ----------------------------------------------------------------------
        def FromDest(filename):
            assert filename.startswith(optional_local_destination_dir), (filename, optional_local_destination_dir)
            filename = filename[len(optional_local_destination_dir):]
            filename = FileSystem.RemoveInitialSep(filename)

            parts = filename.split(os.path.sep)
            parts[0] = parts[0].replace('_', ':')

            return os.path.join(*parts)

        # ----------------------------------------------------------------------

    else:
        if len(source_file_info) == 1:
            common_path = os.path.dirname(source_file_info[0].Name)
        else:
            common_path = FileSystem.GetCommonPath(*[ sfi.Name for sfi in source_file_info ])
            assert common_path

        common_path = FileSystem.AddTrailingSep(common_path)

        # ----------------------------------------------------------------------
        def ToDest(filename):
            assert filename.startswith(common_path), (filename, common_path)
            filename = filename[len(common_path):]

            return os.path.join(optional_local_destination_dir, filename)

        # ----------------------------------------------------------------------
        def FromDest(filename):
            assert filename.startswith(optional_local_destination_dir), (filename, optional_local_destination_dir)
            filename = filename[len(optional_local_destination_dir):]
            filename = FileSystem.RemoveInitialSep(filename)

            return os.path.join(common_path, filename)

        # ----------------------------------------------------------------------

    return ToDest, FromDest

# ----------------------------------------------------------------------
def _Display(work, output_stream, show_dest=False):
    added = OrderedDict()
    modified = OrderedDict()
    removed = []

    for sfi, dfi in six.iteritems(work):
        if sfi is None:
            continue

        if isinstance(dfi, six.string_types):
            added[sfi.Name] = dfi
        else:
            modified[sfi.Name] = dfi.Name

    removed = [ item.Name for item in work.get(None, []) ]

    if show_dest:
        template = "    {source:<100} -> {dest}\n"
    else:
        template = "    {source}\n"

    # ----------------------------------------------------------------------
    def WriteHeader(header):
        output_stream.write(textwrap.dedent(
            """\
            {}
            {}
            """).format( header,
                         '-' * len(header),
                       ))

    # ----------------------------------------------------------------------

    # Added
    WriteHeader("Files to Add ({})".format(len(added)))
    
    for source, dest in six.iteritems(added):
        output_stream.write(template.format( source=source,
                                             dest=dest,
                                           ))
    output_stream.write("\n")

    # Modified
    WriteHeader("Files to Modify ({})".format(len(modified)))

    for source, dest in six.iteritems(modified):
        output_stream.write(template.format( source=source,
                                             dest=dest,
                                           ))
    output_stream.write("\n")

    # Removed
    WriteHeader("Files to Remove ({})".format(len(removed)))

    for item in removed:
        output_stream.write("    {}\n".format(item))

    output_stream.write("\n")

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    try: sys.exit(CommandLine.Main())
    except KeyboardInterrupt: pass
