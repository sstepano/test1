from django.db import models
from django.contrib.auth.models import User

class Auction(models.Model):
    seller = models.ForeignKey(User)
    title = models.CharField(max_length=150)
    description = models.TextField()
    minimum_price = models.FloatField()
    deadline = models.DateTimeField()
    state = models.CharField(max_length=15, default="Active")

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ['title']