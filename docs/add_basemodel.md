# Adding `BaseModel` to an Existing Model

## Handling the `token` Field and Required Migration Changes

When adding `BaseModel` to an existing model that already contains data, Django cannot automatically generate unique values for the new `token` field in a migration. To safely update the database, you must perform a **three-step migration** that:

1. Adds the `token` field without `unique=True`
2. Populates the token for all existing rows
3. Alters the field to enforce uniqueness

---

## Step 1 — Add the `token` field without unique=True

Modify the automatically generated migration so that the `AddField` looks like:

```python
migrations.AddField(
    model_name='yourmodel',
    name='token',
    field=models.CharField(
        max_length=20,
        null=True,
        blank=True,
        editable=False,
    ),
)
```

---

## Step 2 — Populate existing rows with tokens

Inside the same migration file, add:

```python
def populate_tokens(apps, schema_editor):
    YourModel = apps.get_model('yourapp', 'YourModel')
    from cmnsd.models.cmnsd_basemodel import generate_public_id

    for obj in YourModel.objects.all():
        obj.token = generate_public_id()
        obj.save(update_fields=['token'])
```

Then include:

```python
migrations.RunPython(populate_tokens),
```

---

## Step 3 — Enforce uniqueness

Append this `AlterField`:

```python
migrations.AlterField(
    model_name='yourmodel',
    name='token',
    field=models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        editable=False,
    ),
)
```

---

## Full single-file migration example

```python
from django.db import migrations, models

def populate_tokens(apps, schema_editor):
    YourModel = apps.get_model('yourapp', 'YourModel')
    from cmnsd.models.cmnsd_basemodel import generate_public_id

    for obj in YourModel.objects.all():
        obj.token = generate_public_id()
        obj.save(update_fields=['token'])

class Migration(migrations.Migration):

    dependencies = [
        ('yourapp', 'xxxx_previous_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='yourmodel',
            name='token',
            field=models.CharField(
                max_length=20,
                null=True,
                blank=True,
                editable=False,
            ),
        ),

        migrations.RunPython(populate_tokens),

        migrations.AlterField(
            model_name='yourmodel',
            name='token',
            field=models.CharField(
                max_length=20,
                unique=True,
                blank=True,
                editable=False,
            ),
        ),
    ]
```

---

This method ensures:

- No data loss  
- All existing rows get valid unique tokens  
- The field becomes unique only after the data is populated  
