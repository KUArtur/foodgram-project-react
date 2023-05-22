from rest_framework import permissions


class OnlyAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_admin


class IsAdminOrOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
                request.method in permissions.SAFE_METHODS
                or request.user.is_admin
                or obj.author == request.user
        )

    def has_permission(self, request, view):
        return (
                request.method in permissions.SAFE_METHODS
                or request.user.is_authenticated
        )
