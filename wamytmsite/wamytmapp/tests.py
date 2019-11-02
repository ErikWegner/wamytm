from django.test import TestCase
from .models import OrgUnit, get_children


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
            ("A", (
                (3, "A"), (4, "Aa"), (5, "Ab")
            )),
            (8, "C"),
            ("B", (
                (7, "B"), (10, "Ba"), (12, "Bb")
            ))])

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
        result = get_children(org_units, a.id)

        # Assert
        self.assertEquals(result, [
            (4, "Aa"), (5, "Ab")])
