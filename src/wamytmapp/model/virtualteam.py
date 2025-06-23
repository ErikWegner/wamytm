from .base import *

class virtualteam_manager(models.Manager):
    def get_childs(self, orgunit):
        ret = super().all().filter(vt_parent_id=orgunit).values_list('vt_id', flat=True)
        return list(ret)

    
class virtualteam(models.Model):
    vt_id = models.IntegerField(primary_key=True)
    #vt_parent_id = models.IntegerField(null=True)
    vt_parent = models.ForeignKey("virtualteam", on_delete=models.CASCADE)
    vt_name = models.TextField()
    is_privat = models.BooleanField(default=False)
    objects = virtualteam_manager()

    def __str__(self):
        return self.vt_name

class ma2vt_Manager(models.Manager):
    def get_users(self, orgunit):
        orgunit = abs(orgunit)
        orgunits = virtualteam.objects.get_childs(orgunit)
        orgunits.append(orgunit)
        tmp = super().all()
        all_users = super().all().filter(vt__in=orgunits).values_list('user', flat=True)
        return list(all_users)

class ma2vt(models.Model):
    vt = models.ForeignKey(virtualteam, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    objects = ma2vt_Manager()
    def __str__(self):
        return f"{self.vt} <- {self.user}" 