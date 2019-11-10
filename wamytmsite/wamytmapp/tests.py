from django.test import TestCase
from .models import OrgUnit, collect_descendents, get_children


class CreateSelectListItemsFromOrgUnitsTest(TestCase):
    def test_structure1(self):
        """
        a simple structure gets converted to the expected structure
        """
        # Arrange
        org_units = []
        org_units.append(OrgUnit(name="A", id=3))
        org_units.append(OrgUnit(name="B", id=7))
        org_units.append(OrgUnit(name="C", id=8))

        # Act
        result = get_children(org_units)

        # Assert
        self.assertEquals(result, [(3, "A"), (7, "B"), (8, "C")])

    def test_structure2(self):
        """
        A structure with child elements
        """
        # Arrange
        org_units = []
        a = OrgUnit(name="A", id=3)
        b = OrgUnit(name="B", id=7)
        org_units.append(a)
        org_units.append(OrgUnit(name="Aa", id=4, parent=a))
        org_units.append(OrgUnit(name="Ab", id=5, parent=a))
        org_units.append(OrgUnit(name="Ba", id=10, parent=b))
        org_units.append(OrgUnit(name="C", id=8))
        org_units.append(OrgUnit(name="Bb", id=12, parent=b))
        org_units.append(b)

        # Act
        result = get_children(org_units)

        # Assert
        self.assertEquals(result, [
            (3, "A"),
            ("A", (
                (4, "Aa"), (5, "Ab")
            )),
            (7, "B"),
            ("B", (
                (10, "Ba"), (12, "Bb")
            )),
            (8, "C"),
        ])

    def test_structure3(self):
        """
        A structure with child elements
        """
        # Arrange
        org_units = []
        a = OrgUnit(name="A", id=3)
        b = OrgUnit(name="B", id=7)
        org_units.append(a)
        org_units.append(OrgUnit(name="Aa", id=4, parent=a))
        org_units.append(OrgUnit(name="Ab", id=5, parent=a))
        org_units.append(OrgUnit(name="Ba", id=10, parent=b))
        org_units.append(OrgUnit(name="C", id=8))
        org_units.append(OrgUnit(name="Bb", id=12, parent=b))
        org_units.append(b)

        # Act
        result = collect_descendents(org_units, a.id)

        # Assert
        self.assertEquals(result, [4, 5])

    def test_nestedlevels(self):
        """
        A structure with sublevels of children
        """
        # Arrange
        org_units = []

        def adder(name, id, parent):
            ou = OrgUnit(name=name, id=id, parent=parent)
            org_units.append(ou)
            return ou

        # Top level
        t = adder("top", 1, None)
        # Second level
        ou1 = adder("l1-ou1", 10, t)
        ou2 = adder("l1-ou2", 20, t)
        # Third level
        adder("l2-ou1", 11, ou1)
        ou3 = adder("l2-ou2", 12, ou1)
        ou4 = adder("l2-ou3", 21, ou2)
        adder("l2-ou4", 22, ou2)
        # Fourth level
        adder("l3-ou1", 121, ou3)
        adder("l3-ou2", 122, ou3)
        adder("l3-ou3", 211, ou4)
        adder("l3-ou4", 212, ou4)

        # Act
        result = get_children(org_units)

        # Assert
        self.assertSequenceEqual(result, [
            (1, 'top'),

            ('top', ((10, 'l1-ou1'), (20, 'l1-ou2'))),

            ('l1-ou1', ((11, 'l2-ou1'), (12, 'l2-ou2'))),
            ('l1-ou2', ((21, 'l2-ou3'), (22, 'l2-ou4'))),

            ('l2-ou2', ((121, 'l3-ou1'), (122, 'l3-ou2'))),
            ('l2-ou3', ((211, 'l3-ou3'), (212, 'l3-ou4'))),
        ])
