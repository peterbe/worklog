from mongokit import RequireFieldError, ValidationError
import datetime
import unittest
from apps.main.models import Event, User
from apps.eventlog import actions, contexts
from apps.eventlog.models import EventLog
from apps.main.tests.base import BaseModelsTestCase

class ModelsTestCase(BaseModelsTestCase):
    def setUp(self):
        super(ModelsTestCase, self).setUp()
        self.db.connection.register([EventLog, Event, User])

    def test_static_get_eventlogs_by_event(self):
        user = self.db.User()
        event = self.db.Event()
        event.user = user
        event.title = u"Something"
        event.start = event.end = datetime.datetime.now()
        event.all_day = False
        event.save()

        eventlogs = EventLog.get_eventlogs_by_event(event)
        self.assertEqual(eventlogs.count(), 0)

        eventlog1 = self.db.EventLog()
        eventlog1.event = event
        eventlog1.user = user
        eventlog1.action = actions.ACTION_ADD
        eventlog1.context = contexts.CONTEXT_CALENDAR
        eventlog1.save()

        eventlogs = EventLog.get_eventlogs_by_event(event)
        self.assertEqual(eventlogs.count(), 1)
        first = list(eventlogs)[0]
        self.assertEqual(first.action, actions.ACTION_ADD)

        # add another event and we should be able to sort them
        eventlog2 = self.db.EventLog()
        eventlog2.event = event
        eventlog2.user = user
        eventlog2.action = actions.ACTION_EDIT
        eventlog2.context = contexts.CONTEXT_CALENDAR
        eventlog2.modify_date = datetime.datetime.now() + datetime.timedelta(seconds=1)
        eventlog2.save()

        eventlogs = EventLog.get_eventlogs_by_event(event)
        self.assertEqual(eventlogs.count(), 2)
        first, second = list(eventlogs.sort('add_date', 1))
        self.assertEqual(first.action, actions.ACTION_ADD)
        self.assertEqual(second.action, actions.ACTION_EDIT)
        eventlogs.rewind()
        second, first = list(eventlogs.sort('add_date', -1))
        self.assertEqual(first.action, actions.ACTION_ADD)
        self.assertEqual(second.action, actions.ACTION_EDIT)

        # now add some other junk related to some other event
        event2 = self.db.Event()
        event2.user = user
        event2.title = u"Else"
        event2.start = event2.end = datetime.datetime.now()
        event2.all_day = False
        event2.save()


        eventlog1 = self.db.EventLog()
        eventlog1.event = event2
        eventlog1.user = user
        eventlog1.action = actions.ACTION_ADD
        eventlog1.context = contexts.CONTEXT_CALENDAR
        eventlog1.save()

        eventlogs = EventLog.get_eventlogs_by_event(event)
        self.assertEqual(eventlogs.count(), 2)

        eventlogs = EventLog.get_eventlogs_by_event(event2)
        self.assertEqual(eventlogs.count(), 1)
