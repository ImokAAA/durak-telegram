# Generated by Django 3.0.8 on 2020-09-08 09:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0005_auto_20200907_1356'),
    ]

    operations = [
        migrations.AddField(
            model_name='chat',
            name='deck',
            field=models.CharField(default='0', max_length=200),
        ),
        migrations.AddField(
            model_name='chat',
            name='trump',
            field=models.CharField(default='0', max_length=200),
        ),
        migrations.AddField(
            model_name='player',
            name='cards',
            field=models.CharField(default='0', max_length=200),
        ),
        migrations.AlterField(
            model_name='player',
            name='chats',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.Chat'),
        ),
    ]