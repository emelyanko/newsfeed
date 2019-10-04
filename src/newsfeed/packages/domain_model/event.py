"""Events module."""

from typing import Type, Mapping, Sequence
from uuid import UUID, uuid4
from datetime import datetime

from newsfeed.packages.infrastructure.event_storage import EventStorage


class EventFQID:
    """Event fully-qualified identifier."""

    def __init__(self, newsfeed_id: str, event_id: UUID):
        """Initialize object."""
        assert isinstance(newsfeed_id, str)
        self.newsfeed_id = newsfeed_id

        assert isinstance(event_id, UUID)
        self.event_id = event_id

    @property
    def serialized_data(self):
        """Return serialized data."""
        return {
            'newsfeed_id': self.newsfeed_id,
            'event_id': str(self.event_id),
        }


class Event:
    """Event entity."""

    def __init__(self, id: UUID, newsfeed_id: str, data: Mapping, parent_fqid: EventFQID,
                 child_fqids: Sequence[EventFQID], first_seen_at: datetime,
                 published_at: datetime):
        """Initialize entity."""
        assert isinstance(id, UUID)
        self._id = id

        assert isinstance(newsfeed_id, str)
        self._newsfeed_id = newsfeed_id

        assert isinstance(data, Mapping)
        self._data = data

        if parent_fqid is not None:
            assert isinstance(parent_fqid, EventFQID)
        self._parent_fqid = parent_fqid

        assert isinstance(child_fqids, Sequence)
        for child_fqid in child_fqids:
            assert isinstance(child_fqid, EventFQID)
        self._child_fqids = list(child_fqids)

        assert isinstance(first_seen_at, datetime)
        self._first_seen_at = first_seen_at

        if published_at is not None:
            assert isinstance(published_at, datetime)
        self._published_at = published_at

    @property
    def id(self):
        """Return id."""
        return self._id

    @property
    def newsfeed_id(self):
        """Return newsfeed id."""
        return self._newsfeed_id

    @property
    def fqid(self):
        """Return fully-qualified event id."""
        return EventFQID(self.newsfeed_id, self.id)

    @property
    def child_fqids(self):
        """Return list of child FQIDs."""
        return list(self._child_fqids)

    @property
    def data(self):
        """Return data."""
        return self._data

    def track_publishing_time(self):
        """Track event publishing time."""
        self._published_at = datetime.utcnow()

    def track_child_event_fqids(self, child_fqids: Sequence[EventFQID]):
        """Track event child FQIDs."""
        assert isinstance(child_fqids, Sequence)
        for child_fqid in child_fqids:
            assert isinstance(child_fqid, EventFQID)
        self._child_fqids = child_fqids

    @property
    def serialized_data(self):
        """Return serialized data."""
        return {
            'id': str(self._id),
            'newsfeed_id': self._newsfeed_id,
            'data': self._data,
            'parent_fqid': self._parent_fqid.serialized_data if self._parent_fqid else None,
            'child_fqids': [
                child_fqid.serialized_data
                for child_fqid in self._child_fqids
            ],
            'first_seen_at': self._first_seen_at.timestamp(),
            'published_at': self._published_at.timestamp() if self._published_at else None,
        }


class EventFactory:
    """Event entity factory."""

    def __init__(self, cls: Type[Event]):
        """Initialize factory."""
        assert issubclass(cls, Event)
        self._cls = cls

    def create_new(self, newsfeed_id, data, parent_fqid=None, child_fqids=None) -> Event:
        """Create new event."""
        return self._cls(
            id=uuid4(),
            newsfeed_id=newsfeed_id,
            data=data,
            parent_fqid=parent_fqid,
            child_fqids=child_fqids or [],
            first_seen_at=datetime.utcnow(),
            published_at=None,
        )

    def create_from_serialized(self, data) -> Event:
        """Create event from serialized data."""
        return self._cls(
            id=UUID(data['id']),
            newsfeed_id=data['newsfeed_id'],
            data=data['data'],
            parent_fqid=(
                EventFQID(
                    newsfeed_id=data['parent_fqid']['newsfeed_id'],
                    event_id=UUID(data['parent_fqid']['event_id']),
                )
                if data['parent_fqid']
                else None
            ),
            child_fqids=[
                EventFQID(
                    newsfeed_id=data['newsfeed_id'],
                    event_id=UUID(data['event_id']),
                )
                for data in data['child_fqids'] or []
            ],
            first_seen_at=datetime.utcfromtimestamp(data['first_seen_at']),
            published_at=(
                datetime.utcfromtimestamp(data['published_at']) if data['published_at'] else None
            ),
        )


class EventSpecification:
    """Event specification."""

    def __init__(self):
        """Initialize specification."""

    def is_satisfied_by(self, event: Event):
        """Check if event satisfies specification."""
        return True


class EventRepository:
    """Event repository."""

    def __init__(self, factory: EventFactory, storage: EventStorage):
        """Initialize repository."""
        assert isinstance(factory, EventFactory)
        self._factory = factory

        assert isinstance(storage, EventStorage)
        self._storage = storage

    async def add(self, event: Event):
        """Add event to repository."""
        await self._storage.add(event.serialized_data)

    async def get_by_fqid(self, fqid: EventFQID):
        """Return event by its FQID."""
        event_data = await self._storage.get_by_fqid(
            newsfeed_id=fqid.newsfeed_id,
            event_id=str(fqid.event_id),
        )
        return self._factory.create_from_serialized(event_data)

    async def delete_by_fqid(self, fqid: EventFQID):
        """Return event by its FQID."""
        await self._storage.delete_by_fqid(
            newsfeed_id=fqid.newsfeed_id,
            event_id=str(fqid.event_id),
        )

    async def get_newsfeed(self, newsfeed_id):
        """Return newsfeed events."""
        return await self._storage.get_newsfeed(newsfeed_id)
