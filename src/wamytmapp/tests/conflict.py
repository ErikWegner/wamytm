from dataclasses import dataclass

from django.test import Client, TestCase
from django.contrib.auth.models import User

from .helpers import d, createAbsentTimeRangeObject
from ..models import OrgUnit, TimeRange, TimeRangeManager, OrgUnitDelegate, TeamMember


@dataclass
class AllKindRanges:
    splitItem: TimeRange
    deleteItem: TimeRange
    beginItem: TimeRange
    endItem: TimeRange

    def __iter__(self):
        return iter([
            (self.endItem, TimeRangeManager.OVERLAP_NEW_END),
            (self.splitItem, TimeRangeManager.OVERLAP_SPLIT),
            (self.beginItem, TimeRangeManager.OVERLAP_NEW_START),
            (self.deleteItem, TimeRangeManager.OVERLAP_DELETE)])


class ConflictResolverTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('unittestuser1')
        self.user.save()
        self.org_unit = OrgUnit(name='unittestou')
        self.org_unit.save()
        tm = TeamMember(user=self.user, orgunit=self.org_unit)
        tm.save()

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
        sorted_objects = sorted(objects, key=lambda t: t[0].id)
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
        overlap_actions = map(lambda o: F"{o[0].id}:{o[1]}", objects)
        highestId = TimeRange.objects.all().order_by('-id').first().id

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
        del(new_end)
        # startItem has its start date set one day after the new item ends
        new_start = TimeRange.objects.get(id=objects.beginItem.id)
        self.assertEquals(new_start.start, d('2020-08-13').date())
        self.assertNotEqual(new_start.start, objects.beginItem.start.date())
        del(new_start)
        # (1) splitItem: should have a new end and
        new_split1 = TimeRange.objects.get(id=objects.splitItem.id)
        self.assertEquals(new_split1.end, d('2020-08-04').date())
        self.assertNotEqual(new_split1.end, objects.splitItem.end.date())
        self.assertEqual(new_split1.start, objects.splitItem.start.date())
        del(new_split1)
        # (2) splitItem: should create a new item afterwards
        new_items = TimeRange.objects.filter(id__gt=highestId)
        # the splitted item and the post'ed item are 2 items
        self.assertEquals(2, len(new_items))
        new_split2 = new_items[0]
        self.assertEquals(new_split2.start, d('2020-08-13').date())
        self.assertNotEqual(new_split2.start, objects.splitItem.start.date())
        self.assertEqual(new_split2.end, objects.splitItem.end.date())
        del(new_split2)
        del(new_items)
        # assert objects have not changed
        for untouched_object in untouched:
            item = TimeRange.objects.get(id=untouched_object.id)
            self.assertEquals(item, untouched_object)

    def test_adding_new_timerange_without_end_date(self):
        existing_item = self._hasTimeRangeObject('2020-08-01', '2020-08-15')

        c = Client()
        c.force_login(self.user)
        response = c.post(
            '/cal/add', {
                'start': '2020-08-05',
                'orgunit_id': self.org_unit.id,
                'kind': 'a_',
                'overlap_actions': [F"{existing_item.id}:{TimeRangeManager.OVERLAP_SPLIT}"]
            })

        self.assertEquals(302, response.status_code)
        self.assertEquals("/cal/", response.get("Location"))
        new_split1 = TimeRange.objects.get(id=existing_item.id)
        self.assertEquals(new_split1.end, d('2020-08-04').date())
        self.assertNotEqual(new_split1.end, existing_item.end.date())
        self.assertEqual(new_split1.start, existing_item.start.date())
        del(new_split1)

    def test_user_can_query_own_conflicts(self):
        objects = self._createAllKinds()
        sorted_objects = sorted(objects, key=lambda t: t[0].id)
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
                'end': '2020-08-12',
                'uid': self.user.id,
            })
        self.assertEquals(200, response.status_code, response.content)
        self.maxDiff = None
        self.assertJSONEqual(response.content, {'mods': mods})

    def test_user_can_query_conflicts_as_delegate(self):
        """
        Check that otheruser can query first user's items
        """
        otheruser = User.objects.create_user('unittestuser2')
        otheruser.save()
        ouDelegate = OrgUnitDelegate(orgunit=self.org_unit, user=otheruser)
        ouDelegate.save()

        objects = self._createAllKinds()
        sorted_objects = sorted(objects, key=lambda t: t[0].id)
        mods = list(
            map(
                lambda t: {
                    'item': t[0].buildConflictJsonStructure(),
                    'res': t[1]},
                sorted_objects))

        c = Client()
        c.force_login(otheruser)
        response = c.post(
            '/cal/check', {
                'start': '2020-08-05',
                'end': '2020-08-12',
                'uid': self.user.id,
            })
        self.assertEquals(200, response.status_code, response.content)
        self.maxDiff = None
        self.assertJSONEqual(response.content, {'mods': mods})

    def test_user_cannot_query_conflicts(self):
        """
        Check that otheruser cannot query first user's items
        """
        otheruser = User.objects.create_user('unittestuser2')
        otheruser.save()

        objects = self._createAllKinds()
        sorted_objects = sorted(objects, key=lambda t: t[0].id)
        mods = list(
            map(
                lambda t: {
                    'item': t[0].buildConflictJsonStructure(),
                    'res': t[1]},
                sorted_objects))

        c = Client()
        c.force_login(otheruser)
        response = c.post(
            '/cal/check', {
                'start': '2020-08-05',
                'end': '2020-08-12',
                'uid': self.user.id,
            })
        self.assertEquals(403, response.status_code, response.content)

    def test_user_can_submit_own_conflict_actions(self):
        objects = self._createAllKinds()
        untouched = []
        untouched.append(self._hasTimeRangeObject('2020-06-01', '2020-06-15'))
        untouched.append(self._hasTimeRangeObject('2020-05-01', '2020-05-15'))
        untouched.append(self._hasTimeRangeObject('2020-08-05', '2020-08-12'))
        overlap_actions = map(lambda o: F"{o[0].id}:{o[1]}", objects)
        highestId = TimeRange.objects.all().order_by('-id').first().id

        c = Client()
        c.force_login(self.user)
        response = c.post(
            '/cal/add', {
                'start': '2020-08-05',
                'end': '2020-08-12',
                'orgunit_id': self.org_unit.id,
                'kind': 'a_',
                'overlap_actions': overlap_actions,
                'user': self.user.id
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
        del(new_end)
        # startItem has its start date set one day after the new item ends
        new_start = TimeRange.objects.get(id=objects.beginItem.id)
        self.assertEquals(new_start.start, d('2020-08-13').date())
        self.assertNotEqual(new_start.start, objects.beginItem.start.date())
        del(new_start)
        # (1) splitItem: should have a new end and
        new_split1 = TimeRange.objects.get(id=objects.splitItem.id)
        self.assertEquals(new_split1.end, d('2020-08-04').date())
        self.assertNotEqual(new_split1.end, objects.splitItem.end.date())
        self.assertEqual(new_split1.start, objects.splitItem.start.date())
        del(new_split1)
        # (2) splitItem: should create a new item afterwards
        new_items = TimeRange.objects.filter(id__gt=highestId)
        # the splitted item and the post'ed item are 2 items
        self.assertEquals(2, len(new_items))
        new_split2 = new_items[0]
        self.assertEquals(new_split2.start, d('2020-08-13').date())
        self.assertNotEqual(new_split2.start, objects.splitItem.start.date())
        self.assertEqual(new_split2.end, objects.splitItem.end.date())
        del(new_split2)
        del(new_items)
        # assert objects have not changed
        for untouched_object in untouched:
            item = TimeRange.objects.get(id=untouched_object.id)
            self.assertEquals(item, untouched_object)

    def test_user_can_submit_conflict_actions_as_delegate(self):
        objects = self._createAllKinds()
        untouched = []
        untouched.append(self._hasTimeRangeObject('2020-06-01', '2020-06-15'))
        untouched.append(self._hasTimeRangeObject('2020-05-01', '2020-05-15'))
        untouched.append(self._hasTimeRangeObject('2020-08-05', '2020-08-12'))
        overlap_actions = map(lambda o: F"{o[0].id}:{o[1]}", objects)
        highestId = TimeRange.objects.all().order_by('-id').first().id
        otheruser = User.objects.create_user('unittestuser2')
        otheruser.save()
        ouDelegate = OrgUnitDelegate(orgunit=self.org_unit, user=otheruser)
        ouDelegate.save()

        c = Client()
        c.force_login(otheruser)
        response = c.post(
            '/cal/add', {
                'start': '2020-08-05',
                'end': '2020-08-12',
                'orgunit_id': self.org_unit.id,
                'kind': 'a_',
                'overlap_actions': overlap_actions,
                'user': self.user.id
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
        del(new_end)
        # startItem has its start date set one day after the new item ends
        new_start = TimeRange.objects.get(id=objects.beginItem.id)
        self.assertEquals(new_start.start, d('2020-08-13').date())
        self.assertNotEqual(new_start.start, objects.beginItem.start.date())
        del(new_start)
        # (1) splitItem: should have a new end and
        new_split1 = TimeRange.objects.get(id=objects.splitItem.id)
        self.assertEquals(new_split1.end, d('2020-08-04').date())
        self.assertNotEqual(new_split1.end, objects.splitItem.end.date())
        self.assertEqual(new_split1.start, objects.splitItem.start.date())
        del(new_split1)
        # (2) splitItem: should create a new item afterwards
        new_items = TimeRange.objects.filter(id__gt=highestId)
        # the splitted item and the post'ed item are 2 items
        self.assertEquals(2, len(new_items))
        new_split2 = new_items[0]
        self.assertEquals(new_split2.start, d('2020-08-13').date())
        self.assertNotEqual(new_split2.start, objects.splitItem.start.date())
        self.assertEqual(new_split2.end, objects.splitItem.end.date())
        del(new_split2)
        del(new_items)
        # assert objects have not changed
        for untouched_object in untouched:
            item = TimeRange.objects.get(id=untouched_object.id)
            self.assertEquals(item, untouched_object)


    def test_user_cannot_submit_conflict_actions_mixed(self):
        """
        User1 has time range items.
        User2 is delegate for User1.
        """
        objects = self._createAllKinds()
        untouched = []
        untouched.append(self._hasTimeRangeObject('2020-06-01', '2020-06-15'))
        untouched.append(self._hasTimeRangeObject('2020-05-01', '2020-05-15'))
        untouched.append(self._hasTimeRangeObject('2020-08-05', '2020-08-12'))
        overlap_actions = list(map(lambda o: F"{o[0].id}:{o[1]}", objects))
        highestId = TimeRange.objects.all().order_by('-id').first().id
        otheruser = User.objects.create_user('unittestuser2')
        otheruser.save()
        ouDelegate = OrgUnitDelegate(orgunit=self.org_unit, user=otheruser)
        ouDelegate.save()
        mixedObject = createAbsentTimeRangeObject('2020-08-01', '2020-08-10', otheruser, self.org_unit)
        overlap_actions.append(F"{mixedObject.id}:{TimeRangeManager.OVERLAP_DELETE}")

        c = Client()
        c.force_login(otheruser)
        response = c.post(
            '/cal/add', {
                'start': '2020-08-05',
                'end': '2020-08-12',
                'orgunit_id': self.org_unit.id,
                'kind': 'a_',
                'overlap_actions': overlap_actions,
                'user': self.user.id
            })
        self.assertEquals(400, response.status_code, response.content)

    def test_user_cannot_submit_conflict_actions_for_other_user(self):
        """
        User1 has time range items.
        User2 submits changes for User1's time range items, without being a delegate.
        """
        objects = self._createAllKinds()
        untouched = []
        untouched.append(self._hasTimeRangeObject('2020-06-01', '2020-06-15'))
        untouched.append(self._hasTimeRangeObject('2020-05-01', '2020-05-15'))
        untouched.append(self._hasTimeRangeObject('2020-08-05', '2020-08-12'))
        overlap_actions = map(lambda o: F"{o[0].id}:{o[1]}", objects)
        otheruser = User.objects.create_user('unittestuser2')
        otheruser.save()

        c = Client()
        c.force_login(otheruser)
        response = c.post(
            '/cal/add', {
                'start': '2020-08-05',
                'end': '2020-08-12',
                'orgunit_id': self.org_unit.id,
                'kind': 'a_',
                'overlap_actions': overlap_actions,
                'user': self.user.id
            })
        self.assertEquals(400, response.status_code, response.content)
