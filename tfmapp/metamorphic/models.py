from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

# Create your models here.
# FIXME: Add verbose_name to each field

class DBInstance(models.Model):

    class Meta:
	    verbose_name = _('DB Instance')
	    verbose_name_plural = _('DB Instances')

    db_name = models.CharField(_('Database Name'), max_length=20)
    db_user = models.CharField(_('Database User'), max_length=20)
    db_password = models.CharField(_('Database Password'), max_length=20)
    host = models.CharField(_('Host'), max_length=200)
    port = models.IntegerField(_('Port'), default=0)
    user = models.ForeignKey(User, verbose_name=_('User'), on_delete=models.CASCADE)

    def __str__(self):
        return self.db_name


class Query(models.Model):

    class Meta:
        verbose_name = _('Query')
        verbose_name_plural = _('Queries')

    query_id = models.CharField(_('Query ID'), max_length=200, unique="True")
    query_text = models.CharField(_('Query'), max_length=1000)
    instance = models.ForeignKey(DBInstance, on_delete=models.CASCADE)
    user = models.ForeignKey(User, verbose_name=_('User'), on_delete=models.CASCADE)

    def __str__(self):
        return self.query_id