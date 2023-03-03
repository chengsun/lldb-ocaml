#!/usr/bin/env python

import lldb
import struct
import enum

class OCamlTagNamed(enum.Enum):
    FORCING = 244
    CONT = 245
    LAZY = 246
    CLOSURE = 247
    OBJECT = 248
    INFIX = 249
    FORWARD = 250
    ABSTRACT = 251
    STRING = 252
    DOUBLE = 253
    DOUBLE_ARRAY = 254
    CUSTOM = 255

class OCamlTag():
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

class OCamlBlock():
    def __init__(self, ocaml_info, target, pointer):
        self.header_word = ocaml_info.ReadWord(target, pointer)
        self.tag_byte = OCamlTag(self.header_word & 0xFF)
        self.color = (self.header_word >> 8) & 0x3
        self.size_in_words = (self.header_word >> 10)

    def __str__(self):
        return "<block tag={} color={} size={}>".format(self.tag_byte, self.color, self.size_in_words)

class OCamlValue():
    def __init__(self, word):
        self.word = word

    def IsPointer(self): return (self.word & 1) == 0
    def IsInteger(self): return (self.word & 1) == 1
    def GetInteger(self): return (self.word >> 1)
    def DereferencePointer(self, ocaml_info, target):
        return OCamlBlock(ocaml_info, target, self.word)

    def __str__(self):
        if self.IsInteger():
            return "<integer {}>".format(self.GetInteger())
        else:
            return "<pointer 0x{:x}>".format(self.word)

class ReadWordError(BaseException):
    pass

class OCamlInfo():
    def __init__(self, target):
        self.bytes = target.GetAddressByteSize()
        self.bits = self.bytes * 8
        if not (self.bits == 32 or self.bits == 64):
            raise RuntimeError("Unknown system word bits: {}".format(self.bits))

        self.word_type = target.FindFirstType("uint{}_t".format(self.bits)).GetTypedefedType()
        assert self.word_type.GetByteSize() * 8 == self.bits

    def DataGetValue(self, data):
        error = lldb.SBError()
        if self.bits == 32:
            word = data.GetUnsignedInt32(error, 0)
        elif self.bits == 64:
            word = data.GetUnsignedInt64(error, 0)
        if error.Fail():
            raise RuntimeError(error)
        return OCamlValue(word)

    def ReadWord(self, target, address):
        error = lldb.SBError()
        buf = target.process.ReadMemory(address, self.bytes, error)
        if error.Fail():
            raise ReadWordError(error)
        print(buf.hex())
        if self.bits == 32:
            (word,) = struct.unpack("I", buf)
        elif self.bits == 64:
            (word,) = struct.unpack("Q", buf)
        return word

def print_value(debugger, command, exe_ctx, result, internal_dict):
    """Print a value"""
    target = debugger.GetSelectedTarget()

    ocaml_info = OCamlInfo(target)

    data = target.EvaluateExpression(command).Cast(ocaml_info.word_type).GetData()
    if not data.IsValid():
        print("invalid expression")
        return
    value = ocaml_info.DataGetValue(data)

    if value.IsInteger():
        print("{}".format(value))
    else:
        try:
            print("{} -> {}".format(value, value.DereferencePointer(ocaml_info, target)))
        except ReadWordError:
            print("{} -> (couldn't dereference)".format(value))

def second_utility(debugger, command, exe_ctx, result, internal_dict):
    print("I am the second utility")

# And the initialization code to add your commands
def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command container add -h "OCaml utility commands" ocaml')
    debugger.HandleCommand('command script add -f lldb_ocaml.print_value ocaml print-value')
    debugger.HandleCommand('command script add -f lldb_ocaml.second_utility -h "My second utility" ocaml second')
    print('The "ocaml" command has been installed and its subcommands are ready for use.')
