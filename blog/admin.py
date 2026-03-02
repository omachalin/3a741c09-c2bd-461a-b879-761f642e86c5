from django.contrib import admin
from .models import Blog

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'author_fk', 'published_at', 'is_active')
    list_filter = ('is_active', 'published_at', 'author_fk')
    search_fields = ('title', 'content', 'author_fk__username')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('-published_at',)
    autocomplete_fields = ['author_fk', 'image_fk']
