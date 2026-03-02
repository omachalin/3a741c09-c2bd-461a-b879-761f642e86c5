from rest_framework_roles.roles import is_anon, is_user, is_admin

ROLES = {
    'anon': is_anon,
    'user': is_user,
    'admin': is_admin,
    # можно добавить кастомные проверки, если нужно
}
