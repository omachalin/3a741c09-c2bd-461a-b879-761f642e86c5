from django.contrib import admin
from .models import MenuItem, Page, Attachment, TypeMenuItem


@admin.register(TypeMenuItem)
class TypeMenuItemdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code',)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'updated_at', 'created_at')
    search_fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'page_fk', 'url', 'type_menu_fk', 'created_at')
    list_editable = ('order',)
    search_fields = ('name', 'url',)
    list_filter = ('page_fk',)
    autocomplete_fields = ('type_menu_fk', 'page_fk',)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = [
        'file',
    ]

    search_fields = (
        'id',
        'file',
        'original_name',
    )
