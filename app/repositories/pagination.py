from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int

    @property
    def has_next(self) -> bool:
        return self.offset + len(self.items) < self.total
