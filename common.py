#!/usr/bin/env python

import struct
import enum

def reload(module):
    """Polyfill for reloading a module"""

    # Python 3.0 to 3.4
    try:
        from imp import reload
        imp.reload(module)
        return
    except:
        pass

    # Python 3.4+
    try:
        import importlib
        importlib.reload(module)
        return
    except:
        pass

    # Python 2
    reload(module)

class OCamlTagNamed(enum.Enum):
    FORCING = 244
    CONT = 245
    LAZY = 246
    CLOSURE = 247
    OBJECT = 248
    INFIX = 249
    FORWARD = 250

    # Start of "no scan" tags
    ABSTRACT = 251
    STRING = 252
    DOUBLE = 253
    DOUBLE_ARRAY = 254
    CUSTOM = 255

class OCamlTag(object):
    def __init__(self, value):
        self.value = value
        try:
            self.named_value = OCamlTagNamed(value)
        except:
            self.named_value = None

    def __str__(self):
        if self.named_value:
            return str(self.named_value)
        return str(self.value)

class OCamlBlock(object):
    def __init__(self, ocaml_info, header_word):
        self.header_word = header_word
        self.tag_byte = OCamlTag(self.header_word & 0xFF)
        self.color = (self.header_word >> 8) & 0x3
        self.size_in_words = (self.header_word >> 10)

    def __str__(self):
        return "<block tag={} color={} size={}>".format(self.tag_byte, self.color, self.size_in_words)

class OCamlValue(object):
    def __init__(self, word):
        self.word = word

    def IsPointer(self): return (self.word & 1) == 0
    def IsInteger(self): return (self.word & 1) == 1
    def GetInteger(self): return (self.word >> 1)
    def DereferencePointer(self, ocaml_info):
        header_word = ocaml_info.ReadWord(self.word)
        return OCamlBlock(ocaml_info, header_word)

    def __str__(self):
        if self.IsInteger():
            return "<integer {}>".format(self.GetInteger())
        else:
            return "<pointer 0x{:x}>".format(self.word)

class ReadWordError(BaseException):
    pass

class EvaluateExpressionError(BaseException):
    pass

class OCamlInfoBase(object):
    def __init__(self):
        bits = self.GetWordSize()
        if not (bits == 32 or bits == 64):
            raise RuntimeError("Unknown system word bits: {}".format(self.bits))

    def GetWordSize(self):
        """Returns Sys.word_size (32 or 64)"""
        raise NotImplementedError()

    def ReadWord(self, address):
        """Reads a single word from memory at address and returns as an int
        May raise ReadWordError"""
        raise NotImplementedError()

    def EvaluateExpressionAsValue(self, expression):
        """Evaluates an expression string and returns as an OCamlValue
        May raise EvaluateExpressionError"""
        raise NotImplementedError()

def print_value(ocaml_info, command):
    try:
        value = ocaml_info.EvaluateExpressionAsValue(command)
    except EvaluateExpressionError as e:
        print(e)
        return

    if value.IsInteger():
        print("{}".format(value))
    else:
        try:
            print("{} -> {}".format(value, value.DereferencePointer(ocaml_info)))
        except ReadWordError:
            print("{} -> (couldn't dereference)".format(value))
