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

    def __iter__(self):
        return iter([
            (self.endItem, 'end'),
            (self.splitItem, 'spl'),
            (self.beginItem, 'beg'),
            (self.deleteItem, 'del')])


class ConflictResolverTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('unittestuser1')
        self.org_unit = OrgUnit(name='unittestou')
        self.org_unit.save()

    def _hasTimeRangeObject(self, start: str, end: str):
        return createAbsentTimeRangeObject(start, end, self.user, self.org_unit)

    def _overlapResolution(self, start: str, end: str):
        return TimeRange.objects.overlapResolution(d(start).date(), d(end).date(), self.user.id)

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
            return lambda i: i['item']['id'] == needle.id
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
            "end": ["This field is required."]})

    def test_endpoint_responds_with_list(self):
        objects = self._createAllKinds()
        sorted_objects = sorted([
            (objects.endItem, 'end'),
            (objects.splitItem, 'spl'),
            (objects.beginItem, 'beg'),
            (objects.deleteItem, 'del')], key=lambda t: t[0].id)
        mods = list(
            map(
                lambda t: {
                    'item': t[0].buildConflictJsonStructure(),
                    'res': t[1]},
                sorted_objects))

        c = Client()
        c.force_login(self.user)
        response = c.post(
            '/cal/check', {
                'start': '2020-08-05',
                'end': '2020-08-12'
            })
        self.assertEquals(200, response.status_code, response.content)
        self.maxDiff = None
        self.assertJSONEqual(response.content, {'mods': mods})

    def test_adding_new_timerange_with_mods_changes_some_existing_timeranges(self):
        objects = self._createAllKinds()
        untouched = []
        untouched.append(self._hasTimeRangeObject('2020-06-01', '2020-06-15'))
        untouched.append(self._hasTimeRangeObject('2020-05-01', '2020-05-15'))
        untouched.append(self._hasTimeRangeObject('2020-08-05', '2020-08-12'))
        overlap_actions = ",".join(map(lambda o: F"{o[0].id}:{o[1]}", objects))

        c = Client()
        c.force_login(self.user)
        response = c.post(
            '/cal/add', {
                'start': '2020-08-05',
                'end': '2020-08-12',
                'orgunit_id': self.org_unit.id,
                'kind': 'a_',
                'overlap_actions': overlap_actions
            })

        self.assertEquals(302, response.status_code)
        self.assertEquals("/cal/", response.get("Location"))
        # deleteItem should have been deleted
        with self.assertRaisesMessage(TimeRange.DoesNotExist, 'TimeRange matching query does not exist.'):
            TimeRange.objects.get(id=objects.deleteItem.id)
        # endItem has its end date set one day earlier than the new item starts
        new_end = TimeRange.objects.get(id=objects.endItem.id)
        self.assertEquals(new_end.end, d('2020-08-04').date())
        self.assertNotEqual(new_end.end, objects.endItem.end.date())
        # startItem has its start date set one day after the new item ends
        new_start = TimeRange.objects.get(id=objects.beginItem.id)
        self.assertEquals(new_start.start, d('2020-08-13').date())
        self.assertNotEqual(new_start.start, objects.beginItem.start.date())
