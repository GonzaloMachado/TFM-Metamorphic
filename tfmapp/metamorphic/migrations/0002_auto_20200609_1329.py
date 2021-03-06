# Generated by Django 3.0.7 on 2020-06-09 13:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metamorphic', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dbinstance',
            name='db_name',
            field=models.CharField(max_length=20, verbose_name='Database Name'),
        ),
        migrations.AlterField(
            model_name='dbinstance',
            name='db_password',
            field=models.CharField(max_length=20, verbose_name='Database Password'),
        ),
        migrations.AlterField(
            model_name='dbinstance',
            name='db_user',
            field=models.CharField(max_length=20, verbose_name='Database User'),
        ),
    ]
