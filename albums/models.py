from django.db import models

class Album(models.Model):
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255, default='Unknown Artist')
    release_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return self.title

class Photo(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='photos')
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='photos/', null=True, blank=True)
    
    def __str__(self):
        return self.title
