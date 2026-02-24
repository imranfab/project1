"""
Task 4: Role-based access control for file endpoints.
Staff users OR members of the 'file_managers' group can upload/delete files.
"""

from rest_framework.permissions import BasePermission


class IsFileManager(BasePermission):
    message = "You need staff status or the 'file_managers' role to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return request.user.groups.filter(name="file_managers").exists()
