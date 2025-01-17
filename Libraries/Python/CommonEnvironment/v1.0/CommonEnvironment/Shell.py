﻿# ---------------------------------------------------------------------------
# |  
# |  Shell.py
# |  
# |  David Brownell (db@DavidBrownell.com)
# |  
# |  08/08/2015 12:44:56 PM
# |  
# ---------------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2015-18.
# |          
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ---------------------------------------------------------------------------

import os
import stat
import sys
import tempfile
import textwrap

from .CallOnExit import CallOnExit
from .Interface import Interface, abstractmethod, abstractproperty

# ---------------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# |
# |  Public Types
# |
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class Command(object):
    pass
    
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class Comment(Command):
    """A comment within a generated script"""
    def __init__(self, value):
        self.value = value
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class Message(Command):
    """A message displayed within a generated script"""
    def __init__(self, value):
        self.value = value
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class Call(Command):
    """A command invoked in a generated script"""
    def __init__(self, command_line):
        self.command_line = command_line
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class Execute(Command):
    """A program invokved in a generated script"""
    def __init__(self, command_line):
        self.command_line = command_line
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class SymbolicLink(Command):
    """A symbolic link created in a generated script"""
    def __init__(self, link_filename, link_source, is_dir=None):
        self.link_filename = link_filename
        self.link_source = link_source
        self.is_dir = is_dir or os.path.isdir(link_source)
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class Path(Command):
    """Adds items to the system path in a generated script"""
    def __init__(self, item_or_items, preserve_original=True):
        self.items = item_or_items if isinstance(item_or_items, list) else [ item_or_items, ]
        self.preserve_original = preserve_original
    
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class AugmentPath(Command):
    """Adds items to the system path if they don't already exist"""
    def __init__(self, item_or_items):
        self.items = item_or_items if isinstance(item_or_items, list) else [ item_or_items, ]
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class Set(Command):
    """Sets an environment variable in a generated script"""
    def __init__(self, name, value_or_values, preserve_original=True):
        self.name = name
        self.values = value_or_values if isinstance(value_or_values, list) else [ value_or_values, ]
        self.preserve_original = preserve_original
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class AugmentSet(Command):
    """Adds items to the environment variable if they don't already exist"""
    def __init__(self, name, value_or_values):
        self.name = name
        self.values = value_or_values if isinstance(value_or_values, list) else [ value_or_values, ]

# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class Exit(Command):
    """Exists from a generated script"""
    def __init__(self, pause_on_success=False, pause_on_error=False, return_code=None):
        self.pause_on_success = pause_on_success
        self.pause_on_error = pause_on_error
        self.return_code = return_code
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class ExitOnError(Command):
    """Exists from a generated script if an error was encountered"""
    def __init__(self, return_code=None):
        self.return_code = return_code
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class Raw(Command):
    """Writes a raw string to the generated script"""
    def __init__(self, value):
        self.value = value
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class EchoOff(Command):
    """Disables command echoing in a generated script"""
    def __init__(self):
        pass
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class SetCommandPrompt(Command):
    def __init__(self, prompt):
        self.prompt = prompt
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class RemoveFile(Command):
    def __init__(self, filename):
        self.filename = filename
        
# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class RemoveDirectory(Command):
    def __init__(self, directory):
        self.directory = directory

# ---------------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class CopyFile(Command):
    def __init__(self, source, dest):
        self.source = source
        self.dest = dest
        
# ----------------------------------------------------------------------
# <Too few public methods> pylint: disable = R0903
class Move(Command):
    def __init__(self, source, dest):
        self.source = source
        self.dest = dest

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
class Environment(Interface):
    
    # ---------------------------------------------------------------------------
    # |  Ensure that all generic types are available through this class
    Comment                                 = Comment
    Message                                 = Message
    Call                                    = Call
    Execute                                 = Execute
    SymbolicLink                            = SymbolicLink
    Path                                    = Path
    AugmentPath                             = AugmentPath
    Set                                     = Set
    AugmentSet                              = AugmentSet
    Exit                                    = Exit
    ExitOnError                             = ExitOnError
    Raw                                     = Raw
    EchoOff                                 = EchoOff
    SetCommandPrompt                        = SetCommandPrompt
    RemoveFile                              = RemoveFile
    RemoveDirectory                         = RemoveDirectory
    CopyFile                                = CopyFile
    Move                                    = Move

    # ---------------------------------------------------------------------------
    # |
    # |  Public Properties
    # |
    # ---------------------------------------------------------------------------
    @abstractproperty
    def Name(self) : 
        raise Exception("Abstract property")
    
    @abstractproperty
    def CategoryName(self):
        """\
        While Name is the specific name of the OS, CategoryName is the broad category.
        
        For example, with Ubuntu, Name is Ubuntu and CategoryName is Linux.
        """
        raise Exception("Abstract property")
        
    @abstractproperty
    def ScriptExtension(self):
        """\
        File extension used for scripts (eg ".cmd" or ".sh")
        """
        raise Exception("Abstract property")

    @abstractproperty
    def ExecutableExtension(self):
        """\
        File extension used for executables (if any) (eg. ".exe")
        """
        raise Exception("Abstract property")
        
    @abstractproperty
    def AllArgumentsScriptVariable(self):
        """\
        Convension used to indicate all variables should be passed to a script. (eg "%*" or "$@")
        """
        raise Exception("Abstract property")
        
    @abstractproperty
    def EnvironmentVariableDelimiter(self):
        """\
        Delimiter to separate environment variables (eg ";" or ":")
        """
        raise Exception("Abstract property")
        
    @abstractproperty
    def OSVersion(self):
        raise Exception("Abstract property")
        
    @abstractproperty
    def OSArchitecture(self):
        raise Exception("Abstract property")
        
    @abstractproperty
    def PotentialOSVersionDirectoryNames(self):
        """\
        Names of folders that could be used to store operating-specific versions of different files
        (eg [ "10", "8.1", "7", "Vista" ] or [ "14.04", "12.04", ])
        """
        raise Exception("Abstract property")
        
    @abstractproperty
    def HasCaseSensitiveFileSystem(self):
        raise Exception("Abstract property")
        
    @abstractproperty
    def UserDirectory(self):
        """\
        Returns the directory associated with the active user account
        """
        raise Exception("Abstract property")
        
    @abstractproperty
    def TempDirectories(self):
        """\
        Returns a list of directories that are commonly used to store temp files
        """
        raise Exception("Abstract property")

    # ---------------------------------------------------------------------------
    PotentialOSArchitectureDirectoryNames = [ "x86", "x64", ]
    
    # ---------------------------------------------------------------------------
    # |
    # |  Public Methods
    # |
    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def IsActive(platform_name):
        """\
        Return True if the environment is active
        """
        raise Exception("Abstract method")
    
    # ---------------------------------------------------------------------------
    def GenerateCommands(self, command_or_commands):
        commands = command_or_commands if isinstance(command_or_commands, list) else [ command_or_commands, ]
        
        # <Invalid variable name> pylint: disable = C0103
        CommandTypes = [ Comment, 
                         Message,
                         Call,
                         Execute,
                         SymbolicLink,
                         Path,
                         AugmentPath,
                         Set,
                         AugmentSet,
                         Exit,
                         ExitOnError,
                         Raw,
                         EchoOff,
                         SetCommandPrompt,
                         RemoveFile,
                         RemoveDirectory,
                         CopyFile,
                         Move,
                       ]
                       
        results = []
        
        prefix = self._GeneratePrefixCommand()
        if prefix:
            results.append(prefix)

        for command in commands:
            found = False
            for CommandType in CommandTypes:
                if isinstance(command, CommandType):
                    result = getattr(self, "_Generate{}Command".format(CommandType.__name__))(**command.__dict__)
                    if result != None:
                        results.append(result)
                    
                    found = True
                    break

            if not found:
                assert False, (command, type(command))
            
        suffix = self._GenerateSuffixCommand()
        if suffix:
            results.append(suffix)
                
        return '\n'.join(results)
        
    # ----------------------------------------------------------------------
    def ExecuteCommands( self, 
                         commands, 
                         output_stream=None,
                         environment=None,
                       ):
        """\
        Creates a temporary script file, writes the commands to that file,
        and then executes it. Returns the result and output generated during 
        execution.
        """

        from CommonEnvironment.CallOnExit import CallOnExit
        from CommonEnvironment import FileSystem
        from CommonEnvironment import Process

        temp_filename = self.CreateTempFilename(self.ScriptExtension)

        with open(temp_filename, 'w') as f:
            f.write(self.GenerateCommands(commands))

        with CallOnExit(lambda: FileSystem.RemoveFile(temp_filename)):
            self.MakeFileExecutable(temp_filename)

            return Process.Execute( temp_filename, 
                                    output_stream, 
                                    environment=environment,
                                  )

    # ---------------------------------------------------------------------------
    @classmethod
    def EnumEnvironmentVariable(cls, name):
        value = os.getenv(name)
        if not value:
            return
            
        for item in [ item.strip() for item in value.split(cls.EnvironmentVariableDelimiter) ]:
            if item:
                yield item
            
    # ---------------------------------------------------------------------------
    @classmethod
    def CreateScriptName(cls, name):
        ext = cls.ScriptExtension
        if not ext:
            return name
            
        return "{}{}".format(name, ext)
        
    # ---------------------------------------------------------------------------
    @classmethod
    def CreateExecutableName(cls, name):
        ext = cls.ExecutableExtension
        if not ext:
            return name
            
        return "{}{}".format(name, ext)
        
    # ---------------------------------------------------------------------------
    @staticmethod
    def CreateTempFilename(suffix=''):
        filename_handle, filename = tempfile.mkstemp(suffix=suffix)
        os.close(filename_handle)
        os.remove(filename)
        
        return filename
        
    # ---------------------------------------------------------------------------
    @classmethod
    def CreateTempDirectory(cls, suffix=''):
        folder = cls.CreateTempFilename(suffix)
        os.makedirs(folder)
        
        return folder
        
    # ---------------------------------------------------------------------------
    def CreateDataFilename( self,
                            application_name,
                            suffix=".bin",
                          ):
        return os.path.join(self.UserDirectory, "{}{}".format(application_name.replace(' ', '_'), suffix))
    
    # ---------------------------------------------------------------------------
    @staticmethod
    def IsSymLink(filename):
        return os.path.islink(filename)
        
    # ---------------------------------------------------------------------------
    @staticmethod
    def ResolveSymLink(filename):
        return os.path.realpath(filename)
        
    # ---------------------------------------------------------------------------
    @staticmethod
    def DeleteSymLink(filename, command_only=False):
        os.remove(filename)
        
    # ----------------------------------------------------------------------
    def CreateSymbolicLink(self, link_filename, target, is_dir=None):
        """\
        Creating a symbolic link on some systems is cumbersome. This method handles
        the complexity to ensure that it works on all systems, but may be overkill
        for those systems where it is a straighforward process.
        """

        result, output = self.ExecuteCommands(self.SymbolicLink(link_filename, target, is_dir=is_dir))
        if result != 0:
            from .StreamDecorator import StreamDecorator

            raise Exception(textwrap.dedent(
                    """\
                    An error was encountered when generating a symbolic link:
                        {}
                    """).format(StreamDecorator.LeftJustify(output, 4)))

    # ---------------------------------------------------------------------------
    @staticmethod
    def MakeFileExecutable(filename):
        assert os.path.isfile(filename), filename
        os.chmod(filename, stat.S_IXUSR | stat.S_IWUSR | stat.S_IRUSR)
        
    # ----------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def RemoveDir(dir):
        """\
        Removes a directory.
        """
        raise Exception("Abstract Method")

    # ---------------------------------------------------------------------------
    # |
    # |  Private Methods
    # |
    # ---------------------------------------------------------------------------
    @staticmethod
    def _GenerateRawCommand(value):
        return value
        
    # ---------------------------------------------------------------------------
    # ---------------------------------------------------------------------------
    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GeneratePrefixCommand():
        raise Exception("Abstract method")

    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateSuffixCommand():
        raise Exception("Abstract method")

    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateCommentCommand(value):
        raise Exception("Abstract method")
        
    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateMessageCommand(value):
        raise Exception("Abstract method")
        
    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateCallCommand(command_line):
        raise Exception("Abstract method")
        
    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateExecuteCommand(command_line):
        raise Exception("Abstract method")
        
    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateSymbolicLinkCommand(link_filename, link_source, is_dir):
        raise Exception("Abstract method")
    
    # ---------------------------------------------------------------------------
    @classmethod
    def _GeneratePathCommand(cls, items, preserve_original):
        return cls._GenerateSetCommand("PATH", items, preserve_original)
    
    # ---------------------------------------------------------------------------
    @classmethod
    def _GenerateAugmentPathCommand(cls, items):
        return cls._GenerateAugmentSetCommand("PATH", items)
        
    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateSetCommand(name, values, preserve_original):
        raise Exception("Abstract method")
    
    # ---------------------------------------------------------------------------
    @classmethod
    def _GenerateAugmentSetCommand(cls, name, values):
        if not values:
            return

        env_var = os.getenv(name)
        if not env_var:
            current_values = set()
        else:
            current_values = { item.strip() for item in env_var.split(cls.EnvironmentVariableDelimiter) if item.strip() }

        new_values = [ value.strip() for value in values if value.strip() and value.strip() not in current_values ]
        if not new_values:
            return

        return cls._GenerateSetCommand(name, new_values, preserve_original=bool(current_values))

    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateExitCommand(pause_on_success, pause_on_error, return_code):
        raise Exception("Abstract method")
    
    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateExitOnErrorCommand(return_code):
        raise Exception("Abstract method")
    
    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateEchoOffCommand():
        raise Exception("Abstract method")
    
    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateSetCommandPromptCommand(prompt):
        raise Exception("Abstract method")
    
    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateRemoveFileCommand(filename):
        raise Exception("Abstract method")
    
    # ----------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateRemoveDirectoryCommand(directory):
        raise Exception("Abstract method")

    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateCopyFileCommand(source, dest):
        raise Exception("Abstract method")
    
    # ----------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _GenerateMoveCommand(source, dest):
        raise Exception("Abstract method")

# ---------------------------------------------------------------------------
# |
# |  Methods
# |
# ---------------------------------------------------------------------------
def GetPotentialEnvironments():
    from .Impl.Shell.WindowsEnvironment import WindowsEnvironment
    from .Impl.Shell.UbuntuEnvironment import UbuntuEnvironment
    from .Impl.Shell.DebianEnvironment import DebianEnvironment

    return [ WindowsEnvironment,
             UbuntuEnvironment,
             DebianEnvironment,
           ]

# ---------------------------------------------------------------------------
def GetEnvironment():
    # ----------------------------------------------------------------------
    def GetPlatform():
        result = os.getenv("DEVELOPMENT_ENVIRONMENT_LINUX_NAME_OVERRIDE")
        if result:
            return result.lower()

        import platform

        result = platform.dist()
        if result[0]:
            result = result[0].lower()

            # TODO: Keeping Debian distinct from Ubuntu is causing problems; treat
            #       everything as Ubuntu for now.
            if result == "debian":
                result = "ubuntu"

            return result

        try:
            platform_info = os.uname()                      # <Has no member> pylint: disable = E1101
            return platform_info[3].lower()
        except AttributeError:
            pass

        return os.name.lower()
       
    # ----------------------------------------------------------------------

    plat = GetPlatform()

    for env in GetPotentialEnvironments():
        if env.IsActive(plat):
            this_env = env()
            
            # PotentialOSVersionDirectoryNames is optional
            assert not env.PotentialOSVersionDirectoryNames or this_env.OSVersion in env.PotentialOSVersionDirectoryNames, this_env.OSVersion
            assert this_env.OSArchitecture in env.PotentialOSArchitectureDirectoryNames, this_env.OSArchitecture
            assert all(os.path.isdir(dir) for dir in env.TempDirectories)

            return this_env

    assert False, "No environment for '{}'".format(plat)
