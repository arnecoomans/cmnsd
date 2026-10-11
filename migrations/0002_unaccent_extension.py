from django.db import migrations


def create_unaccent(apps, schema_editor):
  # PostgreSQL only (cmnsd.models.search): the other databases have no
  # extensions. Not UnaccentExtension(): that imports psycopg, which a
  # project on SQLite needn't have.
  if schema_editor.connection.vendor == 'postgresql':
    schema_editor.execute('CREATE EXTENSION IF NOT EXISTS unaccent')


class Migration(migrations.Migration):

  dependencies = [
    ('cmnsd', '0001_initial'),
  ]

  operations = [
    migrations.RunPython(create_unaccent, migrations.RunPython.noop),
  ]
