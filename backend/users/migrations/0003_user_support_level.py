from django.db import migrations, models


def ensure_support_level_column(apps, schema_editor):
    User = apps.get_model('users', 'User')
    table_name = User._meta.db_table
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }

    if 'support_level' in columns:
        return

    field = models.CharField(max_length=20, default='agent')
    field.contribute_to_class(User, 'support_level')
    schema_editor.add_field(User, field)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_support_level_column,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='user',
                    name='support_level',
                    field=models.CharField(max_length=20, default='agent'),
                ),
            ],
        ),
    ]
