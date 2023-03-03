#!/usr/bin/env python

import gdb
import sys
import os

sys.path.append(os.path.dirname(os.path.expanduser(__file__)))
try:
    try:
        common.reload(common)
    except NameError:
        import common
finally:
    sys.path.pop()

class OCamlInfo(common.OCamlInfoBase):
    def __init__(self):
        self.word_type = gdb.lookup_type("size_t")
        self.bits = self.word_type.sizeof * 8

        super(OCamlInfo, self).__init__()

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
        try:
            value = gdb.parse_and_eval(expression).cast(self.word_type)
        except gdb.error as e:
            raise common.EvaluateExpressionError(e)
        return common.OCamlValue(int(value))

    def ReadWord(self, address):
        address = gdb.Value(address).cast(self.word_type.pointer())
        try:
            word = address.dereference()
            word.fetch_lazy()
        except gdb.MemoryError as e:
            raise common.ReadWordError(e)
        if word is None:
            raise common.ReadWordError("word is None")
        return int(word)

class OCamlCommand(gdb.Command):
    def __init__(self):
        super(OCamlCommand, self).__init__("ocaml", command_class=gdb.COMMAND_NONE, prefix=True)

class PrintValueCommand(gdb.Command):
    def __init__(self):
        try:
            completer_class = gdb.COMPLETE_EXPRESSION
        except AttributeError:
            completer_class = gdb.COMPLETE_SYMBOL

        super(PrintValueCommand, self).__init__(
            "ocaml print-value",
            command_class=gdb.COMMAND_DATA,
            completer_class=completer_class)

    def invoke(self, argument, from_tty):
        ocaml_info = OCamlInfo()
        common.print_value(ocaml_info, argument)

OCamlCommand()
PrintValueCommand()
print('The "ocaml" command has been installed and its subcommands are ready for use.')
