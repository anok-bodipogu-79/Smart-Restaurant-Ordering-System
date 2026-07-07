from django.db import migrations

def create_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='Kitchen Staff')
    Group.objects.get_or_create(name='Managers')

def revert_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=['Kitchen Staff', 'Managers']).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('restaurant', '0006_auto_20260706_2359'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_groups, revert_groups),
    ]
