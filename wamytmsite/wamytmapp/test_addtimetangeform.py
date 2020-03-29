from django.test import TestCase
from django.contrib.auth.models import User

from .forms import AddTimeRangeForm
from .models import OrgUnit, TimeRange


class AddTimeRangeFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('unittestuser1')
        self.org_unit = OrgUnit(name='unittestou')
        self.org_unit.save()

    def test_kind_choices_has_items(self):
        form = AddTimeRangeForm(user=self.user)

        expectedChoices = [
            ('a_', 'absent'),
            ('p_', 'present'),
            ('m_', 'mobile'),
            ('mp', 'mobile (particular circumstances)')
        ]

        self.assertEqual(expectedChoices, form.fields['kind'].choices)

    def test_get_time_range_with_default_kind_choice(self):
        postData = {
            'start': '2020-03-28',
            'end': '',
            'kind': TimeRange.ABSENT + AddTimeRangeForm.KIND_DEFAULT,
            'orgunit_id': str(self.org_unit.id)
        }
        form = AddTimeRangeForm(data=postData, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

        time_range = form.get_time_range()
        time_range.full_clean()
        time_range.save()

        self.assertEquals(TimeRange.ABSENT, time_range.kind)
        self.assertNotIn(TimeRange.DATA_KINDDETAIL, time_range.data)

    def test_get_time_range_with_subkind_choice(self):
        postData = {
            'start': '2020-03-28',
            'end': '',
            'kind': TimeRange.MOBILE + 'p',
            'orgunit_id': str(self.org_unit.id)
        }
        form = AddTimeRangeForm(data=postData, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

        time_range = form.get_time_range()
        time_range.full_clean()
        time_range.save()

        self.assertEquals(TimeRange.MOBILE, time_range.kind)
        self.assertIn(TimeRange.DATA_KINDDETAIL, time_range.data)
        self.assertEquals('p', time_range.data[TimeRange.DATA_KINDDETAIL])

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
        self.assertEquals('Select a valid choice. m! is not one of the available choices.', form.errors['kind'][0])
