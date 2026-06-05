from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url
from django.core.files.storage import Storage

class CloudinaryStorage(Storage):
    def _save(self, name, content):
        result = upload(content)
        return result['public_id']
    
    def url(self, name):
        url, options = cloudinary_url(name)
        return url
    
    def exists(self, name):
        return False
