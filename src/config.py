from enum import Enum


class IOMemoryMapping(Enum):
    OUT = 0x00007F00
    IN_CTRL = 0x00007F04
    IN = 0x00007F08


REG_NAMES: dict[str, int] = {
    "$zero": 0,
    "$v0": 2,
    "$v1": 3,
    "$a0": 4,
    "$a1": 5,
    "$t0": 8,
    "$t1": 9,
    "$t2": 10,
    "$t3": 11,
    "$t4": 12,
    "$t5": 13,
    "$gp": 28,
    "$sp": 29,
    "$ra": 31,
}

NUM_GPR = 32
DATA_MEM_SIZE = 65536
INST_MEM_SIZE = 4096
