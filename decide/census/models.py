from django.db import models


class Census(models.Model):
    voting_id = models.PositiveIntegerField()
    voter_id = models.PositiveIntegerField()


class Csv(models.Model):
    file_name = models.FileField(upload_to="census/csvs")
    uploaded = models.DateTimeField(auto_now_add=True)
    activated = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.file_name}"

class Meta:
    unique_together = (('voting_id', 'voter_id'),)
