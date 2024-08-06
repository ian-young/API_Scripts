from typing import Any, List, Tuple, Union, Generator

class Node:
    def __init__(
        self,
        name: str,
        *children: "Node",
        balance_factor: Union[int, None] = None
    ) -> None: ...

    name: str
    children: List["Node"]
    balance_factor: Union[int, None]

def RenderTree(node: Node) -> Generator[Tuple[str, str, Node], None, None]: ...
