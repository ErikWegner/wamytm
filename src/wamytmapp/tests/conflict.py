from django.test import TestCase
from django.contrib.auth.models import User

from .helpers import d, createAbsentTimeRangeObject
from ..models import OrgUnit, TimeRange, TimeRangeManager


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
