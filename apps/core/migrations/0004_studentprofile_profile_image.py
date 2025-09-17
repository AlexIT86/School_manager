from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_studentprofile_approved_studentprofile_approved_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='profile_image',
            field=models.ImageField(blank=True, null=True, upload_to='profiles/'),
        ),
    ]


