from typing import NamedTuple


class EEPInfo(NamedTuple):
    rorg: int
    func: int
    func_type: int

    def __repr__(self):
        return f"EEP {self.rorg:02X}-{self.func:02X}-{self.func_type:02X}"


class EO4HAError(Exception):
    """ Base exception for enocean4ha_bridge """

class EO4HAEEPNotSupportedError(EO4HAError):
    """ The given EEP is currently not supported """
    def __init__(self, eep: EEPInfo):
        super().__init__(f"{repr(eep)} is currently not supported.")
