from rest_framework import serializers
from main.serializers import AttachmentSerializer
from .models import Blog
from user.models import User


class BlogUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']
        read_only_fields = ['username', 'first_name', 'last_name']


class BlogSerializer(serializers.ModelSerializer):
    author_fk = BlogUserSerializer(read_only=True)
    image_fk = AttachmentSerializer(read_only=True)

    class Meta:
        model = Blog
        fields = [
            'title',
            'slug',
            'content',
            'image_fk',
            'author_fk',
            'updated_at',
            'created_at',
        ]
        read_only_fields = fields


class BlogPreviewSerializer(serializers.ModelSerializer):
    image_fk = AttachmentSerializer(read_only=True)

    class Meta:
        model = Blog
        fields = [
            'image_fk',
            'slug'
        ]
        read_only_fields = fields
