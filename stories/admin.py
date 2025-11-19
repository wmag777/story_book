from django.contrib import admin
from .models import Project, Character, Scene, PromptTemplate


class CharacterInline(admin.TabularInline):
    model = Character
    extra = 1


class SceneInline(admin.TabularInline):
    model = Scene
    extra = 1
    fields = ['name', 'order', 'prompt', 'approved_image']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'style', 'created_at', 'updated_at']
    list_filter = ['style', 'created_at']
    search_fields = ['name']
    inlines = [CharacterInline, SceneInline]


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'created_at']
    list_filter = ['project', 'created_at']
    search_fields = ['name', 'description']


@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'order', 'has_image', 'created_at']
    list_filter = ['project', 'created_at']
    search_fields = ['name', 'prompt']
    ordering = ['project', 'order']

    def has_image(self, obj):
        return bool(obj.approved_image)
    has_image.boolean = True
    has_image.short_description = 'Has Image'


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'is_active', 'updated_at']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'description', 'template_text']
    readonly_fields = ['variables', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'template_type', 'description', 'is_active')
        }),
        ('Template Configuration', {
            'fields': ('template_text', 'variables'),
            'description': 'Use {variable_name} syntax for placeholders in the template text.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def save_model(self, request, obj, form, change):
        """Clear cache when saving through admin."""
        super().save_model(request, obj, form, change)
        # Clear cache for this template type
        from django.core.cache import cache
        cache_key = f'prompt_template_{obj.template_type}'
        cache.delete(cache_key)
