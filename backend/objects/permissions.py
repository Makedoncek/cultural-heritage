from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.author == request.user or request.user.is_staff


class IsPhotoUploaderOrAdmin(permissions.BasePermission):
    """Дозволяє модифікацію/видалення фото лише його завантажувачу або адміну."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.uploaded_by == request.user or request.user.is_staff


class IsObjectAuthor(permissions.BasePermission):
    """Дозволяє дію (наприклад, reorder) лише автору об'єкта-батька (з nested URL)."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        from .models import CulturalObject
        object_pk = view.kwargs.get('object_pk')
        if not object_pk:
            return False
        try:
            obj = CulturalObject.objects.get(pk=object_pk)
        except CulturalObject.DoesNotExist:
            return False
        return obj.author == request.user or request.user.is_staff
