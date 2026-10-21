from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='QuoteRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('company', models.CharField(blank=True, max_length=160)),
                ('phone', models.CharField(max_length=40)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('needs', models.TextField(max_length=5000)),
                ('quantity', models.CharField(blank=True, max_length=100)),
                ('required_date', models.DateField(blank=True, null=True)),
                ('source', models.CharField(default='website', max_length=40)),
                ('status', models.CharField(choices=[('new', 'New'), ('contacted', 'Contacted'), ('quoted', 'Quoted'), ('closed', 'Closed')], default='new', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
