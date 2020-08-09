import datetime

from ..models import User, TimeRange, OrgUnit


def d(s: str):
    """ Convert the string to a datetime object """
    return datetime.datetime.strptime(s, "%Y-%m-%d")


def createAbsentTimeRangeObject(start: str, end: str, user: User, orgunit: OrgUnit):
    """ Create a time range object """
    startDate = d(start)
    endDate = d(end)
    timeRange = TimeRange(start=startDate, end=endDate, user=user,
                          orgunit=orgunit, kind=TimeRange.ABSENT, data={})
    timeRange.save()
    return timeRange
