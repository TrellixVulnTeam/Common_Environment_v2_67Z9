# ----------------------------------------------------------------------
# |  
# |  __init__.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2016-09-04 18:11:17
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2016.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
import os
import sys

from CommonEnvironment import Interface as _Interface

# If we are importing as part of a unit test, we don't want to include
# these files as it will lead to circular dependencies. A normal import
# will have already include the base modules, meaning there were be '.'s 
# in the __name__.
#
# This is required because this is a __init__ file that is importing sibling
# files into its own namespace. This practice is generally frowned upon, but 
# useful is this particular scenario.

if '.' in __name__:
    from .BoolTypeInfo import BoolTypeInfo
    from .DateTimeTypeInfo import DateTimeTypeInfo
    from .DateTypeInfo import DateTypeInfo
    from .DirectoryTypeInfo import DirectoryTypeInfo
    from .DurationTypeInfo import DurationTypeInfo
    from .EnumTypeInfo import EnumTypeInfo
    from .FilenameTypeInfo import FilenameTypeInfo
    from .FloatTypeInfo import FloatTypeInfo
    from .GuidTypeInfo import GuidTypeInfo
    from .IntTypeInfo import IntTypeInfo
    from .StringTypeInfo import StringTypeInfo
    from .TimeTypeInfo import TimeTypeInfo
    
    from .. import Arity
else:
    from CommonEnvironment.TypeInfo2.FundamentalTypes.BoolTypeInfo import *
    from CommonEnvironment.TypeInfo2.FundamentalTypes.DateTimeTypeInfo import DateTimeTypeInfo
    from CommonEnvironment.TypeInfo2.FundamentalTypes.DateTypeInfo import DateTypeInfo
    from CommonEnvironment.TypeInfo2.FundamentalTypes.DirectoryTypeInfo import DirectoryTypeInfo
    from CommonEnvironment.TypeInfo2.FundamentalTypes.DurationTypeInfo import DurationTypeInfo
    from CommonEnvironment.TypeInfo2.FundamentalTypes.EnumTypeInfo import EnumTypeInfo
    from CommonEnvironment.TypeInfo2.FundamentalTypes.FilenameTypeInfo import FilenameTypeInfo
    from CommonEnvironment.TypeInfo2.FundamentalTypes.FloatTypeInfo import FloatTypeInfo
    from CommonEnvironment.TypeInfo2.FundamentalTypes.GuidTypeInfo import GuidTypeInfo
    from CommonEnvironment.TypeInfo2.FundamentalTypes.IntTypeInfo import IntTypeInfo
    from CommonEnvironment.TypeInfo2.FundamentalTypes.StringTypeInfo import StringTypeInfo
    from CommonEnvironment.TypeInfo2.FundamentalTypes.TimeTypeInfo import TimeTypeInfo
    
    from CommonEnvironment.TypeInfo2 import Arity

# ----------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# |  
# |  Public Types
# |  
# ----------------------------------------------------------------------
class Visitor(_Interface.Interface):

    # ----------------------------------------------------------------------
    @staticmethod
    @_Interface.abstractmethod
    def OnBool(type_info, *args, **kwargs):
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @_Interface.abstractmethod
    def OnDateTime(type_info, *args, **kwargs):
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @_Interface.abstractmethod
    def OnDate(type_info, *args, **kwargs):
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @_Interface.abstractmethod
    def OnDirectory(type_info, *args, **kwargs):
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @_Interface.abstractmethod
    def OnDuration(type_info, *args, **kwargs):
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @_Interface.abstractmethod
    def OnEnum(type_info, *args, **kwargs):
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @_Interface.abstractmethod
    def OnFilename(type_info, *args, **kwargs):
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @_Interface.abstractmethod
    def OnFloat(type_info, *args, **kwargs):
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @_Interface.abstractmethod
    def OnGuid(type_info, *args, **kwargs):
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @_Interface.abstractmethod
    def OnInt(type_info, *args, **kwargs):
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @_Interface.abstractmethod
    def OnString(type_info, *args, **kwargs):
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @_Interface.abstractmethod
    def OnTime(type_info, *args, **kwargs):
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @classmethod
    def Accept(cls, type_info, *args, **kwargs):
        if isinstance(type_info, BoolTypeInfo):
            return cls.OnBool(type_info, *args, **kwargs)
        elif isinstance(type_info, DateTimeTypeInfo):
            return cls.OnDateTime(type_info, *args, **kwargs)
        elif isinstance(type_info, DateTypeInfo):
            return cls.OnDate(type_info, *args, **kwargs)
        elif isinstance(type_info, DirectoryTypeInfo):
            return cls.OnDirectory(type_info, *args, **kwargs)
        elif isinstance(type_info, DurationTypeInfo):
            return cls.OnDuration(type_info, *args, **kwargs)
        elif isinstance(type_info, EnumTypeInfo):
            return cls.OnEnum(type_info, *args, **kwargs)
        elif isinstance(type_info, FilenameTypeInfo):
            return cls.OnFilename(type_info, *args, **kwargs)
        elif isinstance(type_info, FloatTypeInfo):
            return cls.OnFloat(type_info, *args, **kwargs)
        elif isinstance(type_info, GuidTypeInfo):
            return cls.OnGuid(type_info, *args, **kwargs)
        elif isinstance(type_info, IntTypeInfo):
            return cls.OnInt(type_info, *args, **kwargs)
        elif isinstance(type_info, StringTypeInfo):
            return cls.OnString(type_info, *args, **kwargs)
        elif isinstance(type_info, TimeTypeInfo):
            return cls.OnTime(type_info, *args, **kwargs)
        else:
            raise Exception("'{}' was not expected".format(type(type_info)))

# ----------------------------------------------------------------------
# |  
# |  Public Methods
# |  
# ----------------------------------------------------------------------
# <Invalid argument name> pylint: disable = C0103
# <Too many return statements> pylint: disable = R0911
# <Too many braches> pylint: disable = R0912
def CreateSimpleVisitor( onBoolFunc=None,               # def Func(type_info, *args, **kwargs)
                         onDateTimeFunc=None,           # def Func(type_info, *args, **kwargs)
                         onDateFunc=None,               # def Func(type_info, *args, **kwargs)
                         onDirectoryFunc=None,          # def Func(type_info, *args, **kwargs)
                         onDurationFunc=None,           # def Func(type_info, *args, **kwargs)
                         onEnumFunc=None,               # def Func(type_info, *args, **kwargs)
                         onFilenameFunc=None,           # def Func(type_info, *args, **kwargs)
                         onFloatFunc=None,              # def Func(type_info, *args, **kwargs)
                         onGuidFunc=None,               # def Func(type_info, *args, **kwargs)
                         onIntFunc=None,                # def Func(type_info, *args, **kwargs)
                         onStringFunc=None,             # def Func(type_info, *args, **kwargs)
                         onTimeFunc=None,               # def Func(type_info, *args, **kwargs)
                       ):
    # ----------------------------------------------------------------------
    def Empty(*args, **kwargs):
        pass

    # ----------------------------------------------------------------------
    
    onBoolFunc = onBoolFunc or Empty
    onDateTimeFunc = onDateTimeFunc or Empty
    onDateFunc = onDateFunc or Empty
    onDirectoryFunc = onDirectoryFunc or Empty
    onDurationFunc = onDurationFunc or Empty
    onEnumFunc = onEnumFunc or Empty
    onFilenameFunc = onFilenameFunc or Empty
    onFloatFunc = onFloatFunc or Empty
    onGuidFunc = onGuidFunc or Empty
    onIntFunc = onIntFunc or Empty
    onStringFunc = onStringFunc or Empty
    onTimeFunc = onTimeFunc or Empty

    # ----------------------------------------------------------------------
    class SimpleVisitor(Visitor):
        # ----------------------------------------------------------------------
        @staticmethod
        def OnBool(type_info, *args, **kwargs):
            return onBoolFunc(type_info, *args, **kwargs)

        # ----------------------------------------------------------------------
        @staticmethod
        def OnDateTime(type_info, *args, **kwargs):
            return onDateTimeFunc(type_info, *args, **kwargs)

        # ----------------------------------------------------------------------
        @staticmethod
        def OnDate(type_info, *args, **kwargs):
            return onDateFunc(type_info, *args, **kwargs)

        # ----------------------------------------------------------------------
        @staticmethod
        def OnDirectory(type_info, *args, **kwargs):
            return onDirectoryFunc(type_info, *args, **kwargs)

        # ----------------------------------------------------------------------
        @staticmethod
        def OnDuration(type_info, *args, **kwargs):
            return onDurationFunc(type_info, *args, **kwargs)

        # ----------------------------------------------------------------------
        @staticmethod
        def OnEnum(type_info, *args, **kwargs):
            return onEnumFunc(type_info, *args, **kwargs)

        # ----------------------------------------------------------------------
        @staticmethod
        def OnFilename(type_info, *args, **kwargs):
            return onFilenameFunc(type_info, *args, **kwargs)

        # ----------------------------------------------------------------------
        @staticmethod
        def OnFloat(type_info, *args, **kwargs):
            return onFloatFunc(type_info, *args, **kwargs)

        # ----------------------------------------------------------------------
        @staticmethod
        def OnGuid(type_info, *args, **kwargs):
            return onGuidFunc(type_info, *args, **kwargs)

        # ----------------------------------------------------------------------
        @staticmethod
        def OnInt(type_info, *args, **kwargs):
            return onIntFunc(type_info, *args, **kwargs)

        # ----------------------------------------------------------------------
        @staticmethod
        def OnString(type_info, *args, **kwargs):
            return onStringFunc(type_info, *args, **kwargs)

        # ----------------------------------------------------------------------
        @staticmethod
        def OnTime(type_info, *args, **kwargs):
            return onTimeFunc(type_info, *args, **kwargs)

    # ----------------------------------------------------------------------
    
    return SimpleVisitor
