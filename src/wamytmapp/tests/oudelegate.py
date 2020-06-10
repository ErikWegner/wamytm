import datetime
import random
from django.test import Client, TestCase
from django.contrib.auth.models import User

from .helpers import createAbsentTimeRangeObject
from ..models import OrgUnit, TeamMember, TimeRange, OrgUnitDelegate


class OrgUnitDelegatesTests(TestCase):
    USERS_PER_TEAM = 4
    TEAMS_PER_UNIT = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.userindex = 0

    def childOU(self, org_units, prefix, parent_name, count):
        parents = [v for k, v in org_units.items() if k.startswith(parent_name)]
        for i in range(count):
            parent = parents[i % len(parents)]
            id_base = parent.id * 10
            name = F"{prefix}{i + 1}"
            ou = OrgUnit(
                name=name, id=id_base + i, parent=parent)
            ou.save()
            org_units[name] = ou

    def setupDefaultOrgChart(self):
        org_units = {}
        org_units['company'] = OrgUnit(name="company", id=1)
        org_units['company'].save()

        self.childOU(org_units, "branch", 'company', 2)
        self.childOU(org_units, "department", "branch", 6)
        self.childOU(org_units, "unit", "department", 12)
        self.childOU(org_units, "team", "unit", self.TEAMS_PER_UNIT * 12)
        return org_units

    def setupTeamMembers(self, org_units):
        teammembers = []
        teams = [v for k, v in org_units.items() if k.startswith('team')]
        for team in teams:
            for _ in range(self.USERS_PER_TEAM):
                self.userindex = self.userindex + 1
                user = User.objects.create_user(
                    F"testuser{self.userindex}",
                    first_name='John' if self.userindex % 2 == 0 else 'Jane',
                    last_name='Doe' + str(self.userindex))
                tm = TeamMember(user=user, orgunit=team)
                tm.save()
                teammembers.append(tm)
        return teammembers

    def setupLeads(self, org_units: dict):
        ouleaders = []
        for orgunit in org_units.values():
            self.userindex = self.userindex + 1
            user = User.objects.create_user(
                F"testuser{self.userindex}",
                first_name='John' if self.userindex % 2 == 0 else 'Jane',
                last_name='Lead' + str(self.userindex))
            tm = TeamMember(user=user, orgunit=orgunit)
            tm.save()
            ouleaders.append(tm)
            oudelegate = OrgUnitDelegate(orgunit=orgunit, user=user)
            oudelegate.save()
        return ouleaders

    def setUp(self):
        self.org_units = self.setupDefaultOrgChart()
        self.people = self.setupTeamMembers(self.org_units)
        self.leaders = self.setupLeads(self.org_units)

    def test_TeamLeaderHasPersons(self):
        # Arrange
        leader = OrgUnitDelegate.objects.get(orgunit=self.org_units['team12'])

        # Act
        delegatedUsers = OrgUnitDelegate.objects.delegatedUsers(leader.user_id)

        # Assert
        self.assertEqual(len(delegatedUsers), self.USERS_PER_TEAM + 1)

    def test_UnitLeaderHasPersons(self):
        # Arrange
        leader = OrgUnitDelegate.objects.get(orgunit=self.org_units['unit8'])

        # Act
        delegatedUsers = OrgUnitDelegate.objects.delegatedUsers(leader.user_id)

        # Assert
        self.assertEqual(len(delegatedUsers),
                         (self.USERS_PER_TEAM + 1) * self.TEAMS_PER_UNIT + 1)

    def test_UnitAndTeamLeaderHasPersons(self):
        """ The leader is associated to a unit and a team underneath that unit """
        # Arrange
        leader = OrgUnitDelegate.objects.get(orgunit=self.org_units['unit7'])
        teams = OrgUnit.objects.filter(parent=self.org_units['unit7'])
        OrgUnitDelegate(user=leader.user, orgunit=teams[1]).save()

        # Act
        delegatedUsers = OrgUnitDelegate.objects.delegatedUsers(leader.user_id)

        # Assert
        self.assertEqual(len(delegatedUsers),
                         (self.USERS_PER_TEAM + 1) * self.TEAMS_PER_UNIT + 1)

    def test_LeaderInTwoTeamsHasPersons(self):
        """ The leader is associated to two teams """
        # Arrange
        leader = OrgUnitDelegate.objects.get(orgunit=self.org_units['team8'])
        team = OrgUnitDelegate.objects.get(
            orgunit=self.org_units['team1']).orgunit
        OrgUnitDelegate(user=leader.user, orgunit=team).save()

        # Act
        delegatedUsers = OrgUnitDelegate.objects.delegatedUsers(leader.user_id)

        # Assert
        self.assertEqual(len(delegatedUsers),
                         (self.USERS_PER_TEAM + 1) * 2)

    def test_LeaderInTwoUnitsHasPersons(self):
        """ The leader is associated to two units """
        # Arrange
        leader = OrgUnitDelegate.objects.get(orgunit=self.org_units['unit2'])
        team = OrgUnitDelegate.objects.get(
            orgunit=self.org_units['unit5']).orgunit
        OrgUnitDelegate(user=leader.user, orgunit=team).save()

        # Act
        delegatedUsers = OrgUnitDelegate.objects.delegatedUsers(leader.user_id)

        # Assert
        self.assertEqual(len(delegatedUsers),
                         (self.USERS_PER_TEAM + 1) * self.TEAMS_PER_UNIT * 2 + 2)

    def test_CreatedByTeamMemberIsSeenByCreator(self):
        """ The author has the item in the list.

        The time range is created by a team member and
        seen in the admin by the creator. """
        # Arrange
        teammember = random.choice(self.people)
        timerange = createAbsentTimeRangeObject(
            '2020-06-08', '2020-06-10', teammember.user, teammember.orgunit)
        c = Client()
        c.force_login(teammember.user)

        # Act
        response = c.get('/ka/wamytmapp/timerange/')

        # Assert
        self.assertContains(
            response, F'<a href="/ka/wamytmapp/timerange/{timerange.id}/change/">June 8, 2020</a>')

    def test_CreatedByTeamMemberIsSeenByTeamLeader(self):
        """ The team leader has the item in the list.

        The time range is created by a team member and
        seen in the admin by the team leader. """
        # Arrange
        teammember = random.choice(self.people)
        timerange = createAbsentTimeRangeObject(
            '2020-06-08', '2020-06-10', teammember.user, teammember.orgunit)
        leader = OrgUnitDelegate.objects.get(orgunit=teammember.orgunit)
        c = Client()
        c.force_login(leader.user)

        # Act
        response = c.get('/ka/wamytmapp/timerange/')

        # Assert
        self.assertContains(
            response, F'<a href="/ka/wamytmapp/timerange/{timerange.id}/change/">June 8, 2020</a>')

    def test_CreatedByTeamMemberCanAccessEditForm(self):
        """ The author can open the edit form.

        The time range is created by a team member. Its
        edit form can be accessed by the creator. """
        # Arrange
        teammember = random.choice(self.people)
        timerange = createAbsentTimeRangeObject(
            '2020-06-08', '2020-06-10', teammember.user, teammember.orgunit)
        c = Client()
        c.force_login(teammember.user)

        # Act
        response = c.get(F'/ka/wamytmapp/timerange/{timerange.id}/change/')

        # Assert
        self.assertEqual(response.status_code, 200)

    def test_CreatedByTeamMemberAccessToEditFormAllowedForTeamLeader(self):
        """ The team leader can open the edit form.

        The time range is created by a team member. Its
        edit form can be accessed by the team leader. """
        # Arrange
        teammember = random.choice(self.people)
        timerange = createAbsentTimeRangeObject(
            '2020-06-08', '2020-06-10', teammember.user, teammember.orgunit)
        leader = OrgUnitDelegate.objects.get(orgunit=teammember.orgunit)
        c = Client()
        c.force_login(leader.user)

        # Act
        response = c.get(F'/ka/wamytmapp/timerange/{timerange.id}/change/')

        # Assert
        self.assertEqual(response.status_code, 200)

    def _buildPostData(self, timerange):
        postdata = {
            'orgunit': timerange.orgunit_id,
            'start': str(timerange.start.date()),
            'end': str(timerange.end.date()),
            'subkind': 'p_',
            'part_of_day': '',
            'description': 'unittest',
        }
        return postdata

    def test_CreatedByTeamMemberCanSubmitEditForm(self):
        """ The author can submit the edit form.

        The time range is created by a team member. Changes on the
        edit form can be submitted by the creator. """
        # Arrange
        teammember = random.choice(self.people)
        timerange = createAbsentTimeRangeObject(
            '2020-06-08', '2020-06-10', teammember.user, teammember.orgunit)
        itemurl = F'/ka/wamytmapp/timerange/{timerange.id}/change/'
        c = Client()
        c.force_login(teammember.user)

        # Act
        response = c.post(itemurl, self._buildPostData(timerange))

        # Assert
        self.assertEqual(response.status_code, 302)

    def test_CreatedByTeamMemberSubmitEditFormAllowedForTeamLeader(self):
        """ The team leader can submit the edit form.

        The time range is created by a team member. Changes on the
        edit form can be submitted by the team leader. """
        # Arrange
        teammember = random.choice(self.people)
        timerange = createAbsentTimeRangeObject(
            '2020-06-08', '2020-06-10', teammember.user, teammember.orgunit)
        leader = OrgUnitDelegate.objects.get(orgunit=teammember.orgunit)
        itemurl = F'/ka/wamytmapp/timerange/{timerange.id}/change/'
        c = Client()
        c.force_login(leader.user)

        # Act
        response = c.post(itemurl, self._buildPostData(timerange))

        # Assert
        self.assertEqual(response.status_code, 302)

    def test_CreatedByTeamMemberAuthorCanDeleteItem(self):
        """ The author can delete its item. """
        # Arrange
        teammember = random.choice(self.people)
        timerange = createAbsentTimeRangeObject(
            '2020-06-08', '2020-06-10', teammember.user, teammember.orgunit)
        itemurl = F'/ka/wamytmapp/timerange/{timerange.id}/delete/'
        c = Client()
        c.force_login(teammember.user)

        # Act
        response = c.post(itemurl, {'post': 'yes'})

        # Assert
        self.assertEqual(response.status_code, 302)

    def test_CreatedByTeamMemberDeleteIsAllowedForTeamLeader(self):
        """ The team leader can delete the item.

        The time range is created by a team member. The team leader
        can delete the item. """
        # Arrange
        teammember = random.choice(self.people)
        timerange = createAbsentTimeRangeObject(
            '2020-06-08', '2020-06-10', teammember.user, teammember.orgunit)
        leader = OrgUnitDelegate.objects.get(orgunit=teammember.orgunit)
        itemurl = F'/ka/wamytmapp/timerange/{timerange.id}/delete/'
        c = Client()
        c.force_login(leader.user)

        # Act
        response = c.post(itemurl, {'post': 'yes'})

        # Assert
        self.assertEqual(response.status_code, 302)

    def test_TeamLeaderCannotChangeUser(self):
        """ The team leader cannot submit and change the user.

        The time range is created by a team member. Changes on the
        edit form can be submitted by the team leader. Changing
        the associated user is not allowd. """
        # Arrange
        teammember = random.choice(self.people)
        timerange = createAbsentTimeRangeObject(
            '2020-06-08', '2020-06-10', teammember.user, teammember.orgunit)
        leader = OrgUnitDelegate.objects.get(orgunit=teammember.orgunit)
        itemurl = F'/ka/wamytmapp/timerange/{timerange.id}/change/'
        c = Client()
        c.force_login(leader.user)
        postdata = self._buildPostData(timerange)
        postdata['user'] = leader.user.id

        # Act
        response = c.post(itemurl, postdata)

        # Assert
        self.assertEqual(response.status_code, 302)
        modified_timerange = TimeRange.objects.get(pk=timerange.id)
        self.assertEqual(modified_timerange.user.id, timerange.user.id)
