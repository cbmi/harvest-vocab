from django.test import TestCase
from django.core import management
from avocado.models import DataField, DataContext
from avocado.query.translators import registry, Translator
from vocab.translators import VocabularyTranslator
from .models import Ticket, TicketIndex, TicketHolder, TicketThrough


class ItemTestCase(TestCase):
    def setUp(self):
        TicketIndex.objects.db_manager('alt').index()

    def test_ancestors(self):
        tickets = {
            1: [1],
            2: [1, 2],
            3: [3],
            4: [3, 4],
            5: [3, 4, 5],
            6: [3, 6],
            7: [3, 4, 5, 7],
        }

        for ticket in Ticket.objects.using('alt').iterator():
            ancestors = ticket.ancestors(include_self=True).values_list('pk', flat=True)
            self.assertEqual(list(ancestors.all()), tickets[ticket.id])

    def test_descendants(self):
        tickets = {
            1: [2],
            2: [],
            3: [4, 5, 6, 7],
            4: [5, 7],
            5: [7],
            6: [],
            7: [],
        }

        for ticket in Ticket.objects.using('alt').iterator():
            descendants = ticket.descendants().values_list('pk', flat=True)
            self.assertEqual(list(descendants), tickets[ticket.id])

    def test_terminals(self):
        terminals = Ticket.objects.using('alt').filter(terminal=True).values_list('pk', flat=True)
        self.assertEqual(list(terminals), [2, 6, 7])

    def test_requires_any(self):
        # Holder must be assigned at least one of the tickets..
        values = [3]
        ids = TicketThrough.objects.db_manager('alt').requires_any(values, evaluate=True)
        holders = TicketHolder.objects.filter(id__in=ids).values_list('pk', flat=True)
        self.assertEqual(list(holders), [1, 2, 3])

    def test_requires_all(self):
        # Holder must be assigned both tickets..
        values = [1, 3]
        ids = TicketThrough.objects.db_manager('alt').requires_all(values, evaluate=True)
        holders = TicketHolder.objects.filter(id__in=ids).values_list('pk', flat=True)
        self.assertEqual(list(holders), [1, 3])

    def test_excludes_all(self):
        # Holder must not be assigned to both tickets..
        values = [1, 5]
        ids = TicketThrough.objects.db_manager('alt').excludes_all(values, evaluate=True)
        holders = TicketHolder.objects.filter(id__in=ids).values_list('pk', flat=True)
        self.assertEqual(list(holders), [1, 2])

    def test_excludes_any(self):
        # Holder must not be assigned to either tickets..
        values = [1, 2]
        ids = TicketThrough.objects.db_manager('alt').excludes_any(values, evaluate=True)
        holders = TicketHolder.objects.filter(id__in=ids).values_list('pk', flat=True)
        self.assertEqual(list(holders), [2])

    def test_only(self):
        # Holder must be assigned to only these tickets..
        values = [1, 6]

        ids = TicketThrough.objects.db_manager('alt').only(values, evaluate=True)
        holders = TicketHolder.objects.filter(id__in=ids).values_list('pk', flat=True)
        self.assertEqual(list(holders), [3])


class TranslateTestCase(TestCase):
    fixtures = ['initial_data.json']

    # Define translator with defined through model and register it
    class T(VocabularyTranslator):
        through_model = TicketThrough
    registry.register(T, 'test')

    def setUp(self):
        management.call_command('avocado','init','tests', quiet=True)

        # Build item index
        TicketIndex.objects.index()

        # Create the text index DataField
        self.f = DataField(name='Ticket Index Item', app_name='tests',
            model_name='ticketindex', field_name='item')
        self.f.translator = "test"
        self.f.save()

    def test_only(self):
        c = DataContext(json={
            'field': self.f.pk,
            'operator': 'only',
            'value': [1, 6]
        })
        self.assertEqual([3], [x.pk for x in c.apply(tree=TicketHolder)])

    def test_excludes_any(self):
        c = DataContext(json={
            'field': self.f.pk,
            'operator': '-in',
            'value': [1, 2]
        })
        self.assertEqual([2], [x.pk for x in c.apply(tree=TicketHolder)])

    def test_excludes_all(self):
        c = DataContext(json={
            'field': self.f.pk,
            'operator': '-all',
            'value': [1, 5]
        })
        self.assertEqual([1, 2], sorted([x.pk for x in c.apply(tree=TicketHolder)]))

    def test_requires_all(self):
        c = DataContext(json={
            'field': self.f.pk,
            'operator': 'all',
            'value': [1, 3]
        })
        self.assertEqual([1, 3], sorted([x.pk for x in c.apply(tree=TicketHolder)]))

    def test_requires_any(self):
        c = DataContext(json={
            'field': self.f.pk,
            'operator': 'in',
            'value': [3]
        })
        self.assertEqual([1, 2, 3], sorted([x.pk for x in c.apply(tree=TicketHolder)]))
