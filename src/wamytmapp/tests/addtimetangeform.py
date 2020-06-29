from django.test import TestCase
from django.contrib.auth.models import User

from ..config import RuntimeConfig
from ..forms import AddTimeRangeForm
from ..models import OrgUnit, TimeRange


class AddTimeRangeFormTests(TestCase):
    def setUp(self):
        self.runtimeConfig = RuntimeConfig()
        self.user = User.objects.create_user('unittestuser1')
        self.org_unit = OrgUnit(name='unittestou')
        self.org_unit.save()

    def test_kind_choices_has_items(self):
        form = AddTimeRangeForm(user=self.user)

        expectedChoices = [
            ('a_', 'absent'),
            ('p_', 'present'),
            ('m_', 'mobile'),
        ]

        self.assertEqual(expectedChoices, form.fields['kind'].choices)

    def test_get_time_range_with_default_kind_choice(self):
        postData = {
            'start': '2020-03-28',
            'end': '',
            'kind': TimeRange.ABSENT + self.runtimeConfig.KIND_DEFAULT,
            'orgunit_id': str(self.org_unit.id)
        }
        form = AddTimeRangeForm(data=postData, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

        time_range = form.get_time_range()
        time_range.full_clean()
        time_range.save()

        self.assertEquals(TimeRange.ABSENT, time_range.kind)
        self.assertNotIn(TimeRange.DATA_KINDDETAIL, time_range.data)

    def test_get_time_range_with_invalid_subkind_choice(self):
        postData = {
            'start': '2020-03-28',
            'end': '',
            'kind': TimeRange.MOBILE + '!',
            'orgunit_id': str(self.org_unit.id)
        }
        form = AddTimeRangeForm(data=postData, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('kind', form.errors)
        self.assertEquals(
            'Select a valid choice. m! is not one of the available choices.', form.errors['kind'][0])

    def test_get_time_range_with_description(self):
        unittestdescription = 'A description for this item'
        postData = {
            'start': '2020-03-28',
            'end': '',
            'kind': TimeRange.MOBILE + '_',
            'orgunit_id': str(self.org_unit.id),
            'description': unittestdescription
        }
        form = AddTimeRangeForm(data=postData, user=self.user)

        self.assertTrue(form.is_valid(), form.errors)
        time_range = form.get_time_range()
        time_range.full_clean()
        time_range.save()
        self.assertIn(TimeRange.DATA_DESCRIPTION, time_range.data)
        self.assertEquals(
            unittestdescription,
            time_range.data[TimeRange.DATA_DESCRIPTION])

    def test_get_time_range_partial_forenoon(self):
        postData = {
            'start': '2020-03-28',
            'end': '',
            'kind': TimeRange.MOBILE + '_',
            'orgunit_id': str(self.org_unit.id),
            'part_of_day': 'f'
        }
        form = AddTimeRangeForm(data=postData, user=self.user)

        self.assertTrue(form.is_valid(), form.errors)
        time_range = form.get_time_range()
        time_range.full_clean()
        time_range.save()
        self.assertIn(TimeRange.DATA_PARTIAL, time_range.data)
        self.assertEquals(
            'f',
            time_range.data[TimeRange.DATA_PARTIAL])

    def test_get_time_range_partial_afternoon(self):
        postData = {
            'start': '2020-03-28',
            'end': '',
            'kind': TimeRange.MOBILE + '_',
            'orgunit_id': str(self.org_unit.id),
            'part_of_day': 'a'
        }
        form = AddTimeRangeForm(data=postData, user=self.user)

        self.assertTrue(form.is_valid(), form.errors)
        time_range = form.get_time_range()
        time_range.full_clean()
        time_range.save()
        self.assertIn(TimeRange.DATA_PARTIAL, time_range.data)
        self.assertEquals(
            'a',
            time_range.data[TimeRange.DATA_PARTIAL])

    def test_get_time_range_partial_wholeday(self):
        postData = {
            'start': '2020-03-28',
            'end': '',
            'kind': TimeRange.MOBILE + '_',
            'orgunit_id': str(self.org_unit.id),
            'part_of_day': ''
        }
        form = AddTimeRangeForm(data=postData, user=self.user)

        self.assertTrue(form.is_valid(), form.errors)
        time_range = form.get_time_range()
        time_range.full_clean()
        time_range.save()
        self.assertNotIn(TimeRange.DATA_PARTIAL, time_range.data)
