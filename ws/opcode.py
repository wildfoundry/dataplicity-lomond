from __future__ import unicode_literals


class Opcode(object):
    """Enum of websocket opcodes."""
    continuation = 0
    text = 1
    binary = 2
    reserved1 = 3
    reserved2 = 4
    reserved3 = 5
    reserved4 = 6
    reserved5 = 7
    close = 8
    ping = 9
    pong = 0xA
    reserved6 = 0xB
    reserved7 = 0xC
    reserved8 = 0xD
    reserved9 = 0xE
    reserved10 = 0xF


def is_control(opcode):
    """Check if an opcode is a control code."""
    return opcode >= 8


reserved_opcodes = {
    Opcode.reserved1,
    Opcode.reserved2,
    Opcode.reserved3,
    Opcode.reserved4,
    Opcode.reserved5,
    Opcode.reserved6,
    Opcode.reserved7,
    Opcode.reserved8,
    Opcode.reserved9,
    Opcode.reserved10,
}


def is_reserved(opcode):
    """Check if an opcode is reserved."""
    return opcode in reserved_opcodes