import typing

class _C:
    def __init__(self, string: str) -> None: ...
    red: _C = ...
    green: _C = ...
    yellow: _C = ...
    blue: _C = ...
    magenta: _C = ...
    cyan: _C = ...
    white: _C = ...

    on_red: _C = ...
    on_green: _C = ...
    on_yellow: _C = ...
    on_blue: _C = ...
    on_magenta: _C = ...
    on_cyan: _C = ...
    on_white: _C = ...

    bold: _C = ...
    dark: _C = ...
    underline: _C = ...
    blink: _C = ...
    reverse: _C = ...
    concealed: _C = ...

    def __add__(self, other: typing.Union[_C, str]) -> str: ...
    def __radd__(self, other: typing.Union[_C, str]) -> str: ...
    def __str__(self) -> str: ...

c = _C
