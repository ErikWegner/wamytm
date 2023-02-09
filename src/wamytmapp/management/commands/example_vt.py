from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from wamytmapp.models import virtualteam,ma2vt

class Command(BaseCommand):
    help = 'Beispieldaten virtuelle Teams'
    requires_migrations_checks = True
    vts = [
        virtualteam(vt_id=1,vt_name="Meins"),
        virtualteam(vt_id=2,vt_name="Sub-meins1",vt_parent_id=1),
        virtualteam(vt_id=3,vt_name="Sub-meins2",vt_parent_id=1),
        virtualteam(vt_id=4,vt_name="Kolumbus-Projektteam"),
        virtualteam(vt_id=5,vt_name="Architektur",vt_parent_id=4),
        virtualteam(vt_id=6,vt_name="Entwicklung",vt_parent_id=4),
        virtualteam(vt_id=7,vt_name="Projektteam",vt_parent_id=4)
    ]
    ma2vts = [
        ma2vt(id=7,user=User.objects.get(id=188),vt=vts[1]),
        ma2vt(id=8,user=User.objects.get(id=137),vt=vts[2]),
        ma2vt(id=9,user=User.objects.get(id=248),vt=vts[0]),
        ma2vt(id=10,user=User.objects.get(id=112),vt=vts[2]),
        ma2vt(id=11,user=User.objects.get(id=152),vt=vts[1]),
        ma2vt(id=12,user=User.objects.get(id=98),vt=vts[4]),
        ma2vt(id=13,user=User.objects.get(id=44),vt=vts[4]),
        ma2vt(id=14,user=User.objects.get(id=55),vt=vts[5]),
        ma2vt(id=15,user=User.objects.get(id=57),vt=vts[5]),
        ma2vt(id=16,user=User.objects.get(id=36),vt=vts[6]),
        ma2vt(id=17,user=User.objects.get(id=323),vt=vts[6])
    ]

    def removeData(self):
        ma2vt.objects.all().delete()
        virtualteam.objects.all().delete()

    def generateVTs(self):
        for x in self.vts:
            x.save()
        
    def generateMA2VTs(self):
        for x in self.ma2vts:
            x.save()

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Deleting data'))
        self.removeData()
        self.stdout.write(self.style.NOTICE('create VT'))
        self.generateVTs()
        self.stdout.write(self.style.NOTICE('create MA2VT'))
        self.generateMA2VTs()