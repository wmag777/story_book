from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='project_list'),
    path('project/new/', views.ProjectCreateView.as_view(), name='project_create'),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
    path('project/<int:pk>/story-input/', views.story_input, name='story_input'),
    path('project/<int:pk>/viewer/', views.story_viewer, name='story_viewer'),
    path('project/<int:pk>/delete/', views.delete_project, name='project_delete'),
    path('project/<int:pk>/update-style/', views.update_style, name='update_style'),
    path('project/<int:pk>/update-color-scheme/', views.update_color_scheme, name='update_color_scheme'),
    path('project/<int:project_pk>/scene/<int:scene_pk>/', views.scene_manager, name='scene_manager'),
    path('project/<int:project_pk>/scene/<int:scene_pk>/generate/', views.generate_image, name='generate_image'),
    path('project/<int:project_pk>/scene/<int:scene_pk>/generate-ajax/', views.generate_image_ajax, name='generate_image_ajax'),
    path('project/<int:project_pk>/scene/<int:scene_pk>/edit/', views.edit_scene_image, name='edit_scene_image'),
    path('project/<int:project_pk>/scene/<int:scene_pk>/edit-ajax/', views.edit_scene_image_ajax, name='edit_scene_image_ajax'),

    # Character management URLs
    path('project/<int:project_pk>/character/add/', views.character_add, name='character_add'),
    path('project/<int:project_pk>/character/generate/', views.character_generate, name='character_generate'),
    path('project/<int:project_pk>/character/gallery/', views.character_gallery, name='character_gallery'),
    path('project/<int:project_pk>/character/<int:character_pk>/edit/', views.character_edit, name='character_edit'),
    path('project/<int:project_pk>/character/<int:character_pk>/delete/', views.character_delete, name='character_delete'),
    path('project/<int:project_pk>/character/<int:character_pk>/generate-image/', views.generate_character_image_ajax, name='generate_character_image_ajax'),

    # Prompt Template URLs
    path('prompts/', views.prompt_template_list, name='prompt_template_list'),
    path('prompts/<int:pk>/edit/', views.prompt_template_edit, name='prompt_template_edit'),
    path('prompts/<int:pk>/test/', views.prompt_template_test, name='prompt_template_test'),
    path('prompts/<int:pk>/reset/', views.prompt_template_reset, name='prompt_template_reset'),
    path('prompts/clear-cache/', views.clear_prompt_cache, name='clear_prompt_cache'),

    # Settings URLs
    path('settings/', views.generation_settings, name='generation_settings'),
]