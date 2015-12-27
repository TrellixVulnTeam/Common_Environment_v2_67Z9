# ---------------------------------------------------------------------------
# |  
# |  FundamentalTypeInfo.py
# |  
# |  David Brownell (db@DavidBrownell.com)
# |  
# |  12/26/2015 05:12:48 PM
# |  
# ---------------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2015.
# |          
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ---------------------------------------------------------------------------
import os
import sys

from CommonEnvironment
from CommonEnvironment.Interface import *
from CommonEnvironment import Package

# ---------------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ---------------------------------------------------------------------------

TypeInfo = Package.ImportInit()

# ---------------------------------------------------------------------------
# |
# |  Public Types
# |
# ---------------------------------------------------------------------------
class StringModule(object):
    
    # ---------------------------------------------------------------------------
    # |  Public Properties
    @abstractproperty
    def NoneString(self):
        raise Exception("Abstract Property")
    
    @abstractmethod
    def DefaultDelimiter(self):
        raise Exception("Abstract Property")

    # ---------------------------------------------------------------------------
    # |  Public Methods
    @staticmethod
    @abstractmethod
    def SplitString(value):
        raise Exception("Abstract Method")

    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def ToString(type_info, item):
        raise Exception("Abstract method")

    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def GetItemRegularExpressionStrings(type_info):
        raise Exception("Abstract Property")

    # ---------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def FromString(type_info, item, regex_match, regex_string_index):
        raise Exception("Abstract method")
        
# ---------------------------------------------------------------------------
class FundamentalTypeInfo(TypeInfo.TypeInfo):

    # ---------------------------------------------------------------------------
    # |  Public Methods
    @abstractproperty
    def PythonItemRegularExpressionStrings(self):
        raise Exception("Abstract Property")
    
    # ---------------------------------------------------------------------------
    # |  Public Methods
    @classmethod
    def Init(cls, string_module=None):
        if not string_module:
            from PythonStringModule import PythonStringModule
            string_module = PythonStringModule

        cls._string_module = string_module

    # ---------------------------------------------------------------------------
    def FromString(self, value):
        string_module = self._GetOrInit()
        
        if self.Arity.IsOptional and value == string_module.NoneString:
            value = None
        
        elif self.Arity.IsCollection:
            if not isinstance(value, (list, tuple)):
                value = string_module.SplitString(value)
                
            value = [ self.ItemFromString(item) for item in value ]
        else:
            value = self.ItemFromString(value)

        self.ValidateArity(value)
        return value

    # ---------------------------------------------------------------------------
    def ToString(self, value, delimiter=None):
        string_module = self._GetOrInit()

        self.ValidateArity(value)

        if self.Arity.IsOptional and value == None:
            return string_module.NoneString

        elif self.Arity.IsCollection:
            delimiter = delimiter or string_module.DefaultDelimiter

            if not isinstance(value, (list, tuple)):
                value = [ value, ]

            return ( '{}{}'.format( delimiter,
                                    '' if delimiter == '|' else ' ',
                                  )
                   ).join([ self.ItemToString(item) for item in value ])

        else:
            return self.ItemToString(value)
    
    # ---------------------------------------------------------------------------
    def ItemFromString(self, item):
        string_module = self._GetOrInit()
        
        if not hasattr(self, "_regexes"):
            self._regexes = {}

        if self.__class__ not in self._regexes:
            self._regexes[self.__class__] = [ re.compile(regex) for regex in string_module.GetItemRegularExpressionStrings(self) ]

        # ---------------------------------------------------------------------------
        class NoneType(object): pass

        def GetString():
            for index, regex in enumerate(self._regexes[self.__class__]):
                match = regex.match(item)
                if match:
                    return string_module.FromString(self, item, match, index)
                    
            return NoneType

        # ---------------------------------------------------------------------------
        
        result = GetString()
        if result == NoneType:
            raise Exception("'{}' is not a valid '{}': {}" \
                                .format( item,
                                         self._GetExpectedTypeString(),
                                         self.ConstraintsDesc or ', '.join([ "'{}'".format(regex) for regex in string_module.GetItemRegularExpressionStrings(self) ]),
                                       ))

        item = result
        self.ValidateItem(item)

        return self.PostprocessItem(item)

    # ---------------------------------------------------------------------------
    def ItemToString(self, item):
        string_module = self._GetOrInit()

        self.ValidateItem(item)
        return string_module.ToString(self.__class__, item)

    # ---------------------------------------------------------------------------
    # ---------------------------------------------------------------------------
    # ---------------------------------------------------------------------------
    def _GetOrInit(self):
        if not hasattr(type(self), "_string_module"):
            type(self).Init()

        return _string_module
    