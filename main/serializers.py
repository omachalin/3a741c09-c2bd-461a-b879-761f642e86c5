from rest_framework import serializers
from .models import (MenuItem, Page, Attachment)


class AttachmentSerializer(serializers.ModelSerializer):
    file = serializers.CharField()

    class Meta:
        model = Attachment
        fields = [
            'id',
            'file',
            'filesize',
            'original_name',
            'object_id',
            'created_at',
        ]
        read_only_fields = fields


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['title', 'slug', 'meta', 'updated_at', 'created_at']
        read_only_fields = ['title', 'slug', 'meta', 'updated_at', 'created_at']


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ['name', 'page_fk', 'url', 'order', 'updated_at', 'created_at']
        read_only_fields = ['name', 'page_fk', 'url', 'order', 'updated_at', 'created_at']