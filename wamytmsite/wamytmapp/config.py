from django.utils.translation import pgettext_lazy

from .models import TimeRange


class RuntimeConfig:
    KIND_DEFAULT = '_'
    KIND_LABEL = 'label'
    KIND_ENABLED = 'enabled'
    TimeRangeChoices = None
    TimeRangeViewsLegend = None

    def __init__(self):
        self.initTimeRangeChoicesAndViewsLegend()

    def timeRangeChoicesConfig(self):
        return {
            TimeRange.ABSENT: {
                RuntimeConfig.KIND_DEFAULT: True
            },
            TimeRange.PRESENT: {
                RuntimeConfig.KIND_DEFAULT: True
            },
            TimeRange.MOBILE: {
                RuntimeConfig.KIND_DEFAULT: True,
                'p': {
                    RuntimeConfig.KIND_LABEL: pgettext_lazy(
                        'TimeRangeChoice', 'mobile (particular circumstances)'),
                    RuntimeConfig.KIND_ENABLED: False,
                }
            }
        }

    def initTimeRangeChoicesAndViewsLegend(self):
        VIEWS_LEGEND = {
            TimeRange.ABSENT: pgettext_lazy('TimeRangeChoice', 'absent'),
            TimeRange.PRESENT: pgettext_lazy('TimeRangeChoice', 'present'),
            TimeRange.MOBILE: pgettext_lazy('TimeRangeChoice', 'mobile')
        }
        basechoices = [
            TimeRange.ABSENT,
            TimeRange.PRESENT,
            TimeRange.MOBILE
        ]
        kindchoices_config = self.timeRangeChoicesConfig()
        choices = []
        viewslegend = {}

        for basechoice in basechoices:
            kindchoice_config = kindchoices_config[basechoice]
            for configkey in kindchoice_config.keys():
                if configkey == RuntimeConfig.KIND_DEFAULT:
                    choices.append(
                        (basechoice + '_', VIEWS_LEGEND[basechoice]))
                    viewslegend[basechoice] = VIEWS_LEGEND[basechoice]
                    continue
                if kindchoice_config[configkey][RuntimeConfig.KIND_ENABLED]:
                    choices.append(
                        (basechoice + configkey, kindchoice_config[configkey][RuntimeConfig.KIND_LABEL]))
                viewslegend[basechoice +
                            configkey] = kindchoice_config[configkey][RuntimeConfig.KIND_LABEL]

        RuntimeConfig.TimeRangeChoices = choices
        RuntimeConfig.TimeRangeViewsLegend = viewslegend
