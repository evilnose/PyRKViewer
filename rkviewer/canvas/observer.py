"""Classes for the observer-Subject interface. See https://en.wikipedia.org/wiki/Observer_pattern
"""
import abc
from typing import Callable, Generic, List, Set, TypeVar


T = TypeVar('T')


class Observer(abc.ABC, Generic[T]):
    """Observer abstract base class; encapsulates object of type T."""

    def __init__(self, update_callback: Callable[[T], None]):
        self.update = update_callback


class Subject(Generic[T]):
    """Subject abstract base class; encapsulates object of type T."""
    _observers: List[Observer]
    _item: T

    def __init__(self, item):
        self._observers = list()
        self._item = item

    def attach(self, observer: Observer):
        """Attach an observer."""
        self._observers.append(observer)

    def detach(self, observer: Observer):
        """Detach an observer."""
        self._observers.remove(observer)

    def notify(self) -> None:
        """Trigger an update in each Subject."""

        for observer in self._observers:
            observer.update(self._item)


class SetSubject(Subject[Set[T]]):
    """Subject class that encapsulates a set."""

    def __init__(self, *args):
        super().__init__(set(*args))

    def item_copy(self) -> Set:
        """Return a copy of the encapsulated set."""
        return set(self._item)

    def set_item(self, item: Set):
        """Update the value of the item, notifying observers if the new value differs from the old.
        """
        equal = self._item == item
        self._item = item
        if not equal:
            self.notify()

    def remove(self, el: T):
        """Remove an element from the set, notifying observers if the set changed."""
        equal = el not in self._item
        self._item.remove(el)
        if not equal:
            self.notify()

    def add(self, el: T):
        """Add an element from the set, notifying observers if the set changed."""
        equal = el in self._item
        self._item.add(el)
        if not equal:
            self.notify()
