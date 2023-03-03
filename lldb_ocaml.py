#!/usr/bin/env python

import lldb
import struct
try:
    common.reload(common)
except NameError:
    import common

class OCamlInfo(common.OCamlInfoBase):
    def __init__(self, debugger, exe_ctx, internal_dict):
        self.debugger = debugger
        self.exe_ctx = exe_ctx
        self.internal_dict = internal_dict

        target = self.debugger.GetSelectedTarget()
        self.bytes = target.GetAddressByteSize()
        self.bits = self.bytes * 8

        self.word_type = target.FindFirstType("uint{}_t".format(self.bits)).GetTypedefedType()
        assert self.word_type.GetByteSize() * 8 == self.bits

        super().__init__()

    def GetWordSize(self):
        return self.bits

    def _DataGetWord(self, data):
        error = lldb.SBError()
        if self.bits == 32:
            word = data.GetUnsignedInt32(error, 0)
        elif self.bits == 64:
            word = data.GetUnsignedInt64(error, 0)
        if error.Fail():
            raise RuntimeError(error)
        return word

    def EvaluateExpressionAsValue(self, expression):
        target = self.debugger.GetSelectedTarget()

        data = target.EvaluateExpression(expression).Cast(self.word_type).GetData()
        if not data.IsValid():
            raise common.EvaluateExpressionError("invalid expression")
        try:
            word = self._DataGetWord(data)
        except RuntimeError as e:
            raise common.EvaluateExpressionError(e)
        return common.OCamlValue(word)

    def ReadWord(self, address):
        target = self.debugger.GetSelectedTarget()

        error = lldb.SBError()
        buf = target.process.ReadMemory(address, self.bytes, error)
        if error.Fail():
            raise common.ReadWordError(error)
        return self.UnpackWord(buf)


def print_value(debugger, command, exe_ctx, result, internal_dict):
    """Print a value"""
    ocaml_info = OCamlInfo(debugger, exe_ctx, internal_dict)
    common.print_value(ocaml_info, command)

def second_utility(debugger, command, exe_ctx, result, internal_dict):
    print("I am the second utility")

# And the initialization code to add your commands
def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command container add -h "OCaml utility commands" ocaml')
    debugger.HandleCommand('command script add -f lldb_ocaml.print_value ocaml print-value')
    debugger.HandleCommand('command script add -f lldb_ocaml.second_utility -h "My second utility" ocaml second')
    print('The "ocaml" command has been installed and its subcommands are ready for use.')
