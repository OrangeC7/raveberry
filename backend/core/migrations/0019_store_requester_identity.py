from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_alter_setting_value"),
    ]

    operations = [
        migrations.AddField(
            model_name="queuedsong",
            name="requester_ip",
            field=models.CharField(blank=True, default="", max_length=45),
        ),
        migrations.AddField(
            model_name="queuedsong",
            name="requester_session_key",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="currentsong",
            name="requester_ip",
            field=models.CharField(blank=True, default="", max_length=45),
        ),
        migrations.AddField(
            model_name="currentsong",
            name="requester_session_key",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
    ]
