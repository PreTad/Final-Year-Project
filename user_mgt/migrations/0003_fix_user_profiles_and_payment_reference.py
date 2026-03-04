from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("backend", "0002_physicalmaterial_departmenthead_member_borrow_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="payment",
            old_name="transaction_refernce",
            new_name="transaction_reference",
        ),
        migrations.AlterField(
            model_name="departmenthead",
            name="user_id",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="department_head",
                to="backend.user",
            ),
        ),
        migrations.AlterField(
            model_name="member",
            name="user_id",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="member",
                to="backend.user",
            ),
        ),
        migrations.AlterField(
            model_name="return",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="return_material",
                to="backend.staff",
            ),
        ),
        migrations.AlterField(
            model_name="staff",
            name="user_id",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="staff",
                to="backend.user",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("STACK STAFF", "STACK STAFF"),
                    ("TECHNICAL STAFF", "TECHNICAL STAFF"),
                    ("FRONT DESK STAFF", "FRONT DESK STAFF"),
                    ("ADMIN", "ADMIN"),
                    ("DEPARTMENT HEAD", "DEPARTMENT HEAD"),
                    ("MEMBER", "MEMBER"),
                    ("SUPER ADMIN", "SUPER ADMIN"),
                ],
                default="MEMBER",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="status",
            field=models.CharField(
                choices=[
                    ("ACTIVE", "ACTIVE"),
                    ("INACTIVE", "INACTIVE"),
                    ("SUSPENDED", "SUSPENDED"),
                    ("DEACTIVATED", "DEACTIVATED"),
                ],
                default="ACTIVE",
                max_length=30,
            ),
        ),
    ]
