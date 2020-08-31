import abc
from typing import Callable, FrozenSet, Generic, List, Set, TypeVar


T = TypeVar('T')


class Observer(abc.ABC, Generic[T]):
    def __init__(self, update_callback: Callable[[T], None]):
        self.update = update_callback


class Subject(Generic[T]):
    _observers: List[Observer]
    _item: T

    def __init__(self, item):
        self._observers = list()
        self._item = item

    def attach(self, observer: Observer):
        self._observers.append(observer)

    def detach(self, observer: Observer):
        self._observers.remove(observer)

    def notify(self) -> None:
        """
        Trigger an update in each subscriber.
        """

        for observer in self._observers:
            observer.update(self._item)


class SetSubject(Subject[Set[T]]):
    def __init__(self, *args):
        super().__init__(set(*args))

    def item_copy(self) -> Set:
        return set(self._item)

    def set_item(self, item: Set):
        self._item = item
        self.notify()

    def remove(self, el: T):
        self._item.remove(el)
        self.notify()

    def add(self, el: T):
        self._item.add(el)
        self.notify()
    