"""Permissions for the profile_app API.

The profile endpoints use IsOwnerOrReadOnly from core.permissions,
because offers_app needs the same rule. No own permission is needed here.
"""
