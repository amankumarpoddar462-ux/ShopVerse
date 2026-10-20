from django.db import migrations, models


def ensure_support_approved_column(apps, schema_editor):
    User = apps.get_model('users', 'User')
    table_name = User._meta.db_table
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }

    if 'support_approved' in columns:
        return

    field = models.BooleanField(default=True)
    field.contribute_to_class(User, 'support_approved')
    schema_editor.add_field(User, field)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_support_approved_column,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='user',
                    name='support_approved',
                    field=models.BooleanField(default=True),
                ),
            ],
        ),
    ]
