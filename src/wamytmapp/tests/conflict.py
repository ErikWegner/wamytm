from dataclasses import dataclass

from django.test import Client, TestCase
from django.contrib.auth.models import User

from .helpers import d, createAbsentTimeRangeObject
from ..models import OrgUnit, TimeRange, TimeRangeManager


@dataclass
class AllKindRanges:
    splitItem: TimeRange
    deleteItem: TimeRange
    beginItem: TimeRange
    endItem: TimeRange


class ConflictResolverTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('unittestuser1')
        self.org_unit = OrgUnit(name='unittestou')
        self.org_unit.save()

    def _hasTimeRangeObject(self, start: str, end: str):
        return createAbsentTimeRangeObject(start, end, self.user, self.org_unit)

    def _overlapResolution(self, start: str, end: str):
        return TimeRange.objects.overlapResolution(d(start).date(), d(end).date(), self.org_unit)

    def _assertMods(self, r, kind):
        self.assertTrue('mods' in r, 'Key \'mods\' exists')
        self.assertEquals(1, len(r['mods']), 'Number of mods')
        self.assertEquals(r['mods'][0]['res'], kind)

    def _createAllKinds(self):
        splitItem = self._hasTimeRangeObject('2020-08-01', '2020-08-15')
        deleteItem = self._hasTimeRangeObject('2020-08-07', '2020-08-10')
        beginItem = self._hasTimeRangeObject('2020-08-09', '2020-08-18')
        endItem = self._hasTimeRangeObject('2020-08-01', '2020-08-10')

        return AllKindRanges(splitItem, deleteItem, beginItem, endItem)

    def test_new_start_overlaps_existing_item(self):
        self._hasTimeRangeObject('2020-08-03', '2020-08-07')

        r = self._overlapResolution('2020-08-05', '2020-08-09')

        self._assertMods(r, TimeRangeManager.OVERLAP_NEW_END)

    def test_new_end_overlaps_existing_item(self):
        self._hasTimeRangeObject('2020-08-05', '2020-08-09')

        r = self._overlapResolution('2020-08-03', '2020-08-06')

        self._assertMods(r, TimeRangeManager.OVERLAP_NEW_START)

    def test_new_start_obsoletes_existing_item(self):
        self._hasTimeRangeObject('2020-08-03', '2020-08-07')

        r = self._overlapResolution('2020-08-03', '2020-08-09')

        self._assertMods(r, TimeRangeManager.OVERLAP_DELETE)

    def test_new_end_obsoletes_existing_item(self):
        self._hasTimeRangeObject('2020-08-05', '2020-08-09')

        r = self._overlapResolution('2020-08-03', '2020-08-09')

        self._assertMods(r, TimeRangeManager.OVERLAP_DELETE)

    def test_new_timerange_overlaps_existing_item(self):
        self._hasTimeRangeObject('2020-08-05', '2020-08-07')

        r = self._overlapResolution('2020-08-03', '2020-08-09')

        self._assertMods(r, TimeRangeManager.OVERLAP_DELETE)

    def test_existing_item_overlaps_new_timerange(self):
        self._hasTimeRangeObject('2020-08-03', '2020-08-09')

        r = self._overlapResolution('2020-08-05', '2020-08-07')

        self._assertMods(r, TimeRangeManager.OVERLAP_SPLIT)

    def test_new_item_matches_existing_item(self):
        self._hasTimeRangeObject('2020-08-05', '2020-08-07')

        r = self._overlapResolution('2020-08-05', '2020-08-07')

        self._assertMods(r, TimeRangeManager.OVERLAP_DELETE)

    def test_all_of_them(self):
        splitItem = self._hasTimeRangeObject('2020-08-01', '2020-08-15')
        deleteItem = self._hasTimeRangeObject('2020-08-07', '2020-08-10')
        beginItem = self._hasTimeRangeObject('2020-08-09', '2020-08-18')
        endItem = self._hasTimeRangeObject('2020-08-01', '2020-08-10')

        r = self._overlapResolution('2020-08-05', '2020-08-12')

        self.assertTrue('mods' in r, 'Key \'mods\' exists')
        self.assertEquals(4, len(r['mods']), 'Number of mods')

        def f(needle):
            return lambda i: i['item'].id == needle.id
        modSplitItem = list(filter(f(splitItem), r['mods']))[0]
        self.assertEquals(modSplitItem['res'], TimeRangeManager.OVERLAP_SPLIT)
        modDeleteItem = list(filter(f(deleteItem), r['mods']))[0]
        self.assertEquals(modDeleteItem['res'],
                          TimeRangeManager.OVERLAP_DELETE)
        modBeginItem = list(filter(f(beginItem), r['mods']))[0]
        self.assertEquals(modBeginItem['res'],
                          TimeRangeManager.OVERLAP_NEW_START)
        modEndItem = list(filter(f(endItem), r['mods']))[0]
        self.assertEquals(modEndItem['res'], TimeRangeManager.OVERLAP_NEW_END)

    def test_endpoint_needs_auth(self):
        self._createAllKinds()

        c = Client()
        response = c.post(
            '/cal/check', {'begin': '2020-08-05', 'end': '2020-08-12'})
        self.assertEquals(403, response.status_code)

    def test_endpoint_handles_get(self):
        self._createAllKinds()

        c = Client()
        c.force_login(self.user)
        response = c.get('/cal/check')
        self.assertEquals(400, response.status_code)

    def test_endpoint_returns_list_of_errors(self):
        self._createAllKinds()

        c = Client()
        c.force_login(self.user)
        response = c.post('/cal/check')
        self.assertEquals(400, response.status_code)
        self.assertJSONEqual(response.content, {
            "start": ["This field is required."],
            "end": ["This field is required."],
            "ou": ["This field is required."]})

    def test_endpoint_responds_with_list(self):
        self._createAllKinds()

        c = Client()
        c.force_login(self.user)
        response = c.post(
            '/cal/check', {
                'start': '2020-08-05',
                'end': '2020-08-12',
                'ou': self.org_unit.id})
        self.assertEquals(200, response.status_code, response.content)
        self.assertJSONEqual(response.content, {'mods': [
            {'item': 1, 'res': 'del'}
        ]})
