from rest_framework.throttling import UserRateThrottle


class PhotoUploadThrottle(UserRateThrottle):
    scope = 'photo_upload'
