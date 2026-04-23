from django.db import migrations, models


def _swap_member_fk_to_user(apps, schema_editor):
    Member = apps.get_model("backend", "Member")
    Reservation = apps.get_model("transactions", "Reservation")
    Borrow = apps.get_model("transactions", "Borrow")
    Circulation = apps.get_model("transactions", "Circulation")

    def _update(model):
        for obj in model.objects.all().only("id", "member_id"):
            member_id = obj.member_id
            if not member_id:
                continue
            member = Member.objects.filter(id=member_id).only("user_id_id").first()
            if member and member.user_id_id:
                obj.member_id = member.user_id_id
                obj.save(update_fields=["member_id"])

    _update(Reservation)
    _update(Borrow)
    _update(Circulation)


def _swap_member_fk_to_member(apps, schema_editor):
    Member = apps.get_model("backend", "Member")
    Reservation = apps.get_model("transactions", "Reservation")
    Borrow = apps.get_model("transactions", "Borrow")
    Circulation = apps.get_model("transactions", "Circulation")

    def _update(model):
        for obj in model.objects.all().only("id", "member_id"):
            user_id = obj.member_id
            if not user_id:
                continue
            member = Member.objects.filter(user_id_id=user_id).only("id").first()
            if member:
                obj.member_id = member.id
                obj.save(update_fields=["member_id"])

    _update(Reservation)
    _update(Borrow)
    _update(Circulation)


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0004_fix_reservation_fk_columns"),
        ("backend", "0008_alter_library_staff_id"),
    ]

    operations = [
        migrations.RenameField(
            model_name="reservation",
            old_name="member_id",
            new_name="member",
        ),
        migrations.AlterField(
            model_name="reservation",
            name="member",
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name="reservations",
                to="backend.user",
            ),
        ),
        migrations.AlterField(
            model_name="borrow",
            name="member",
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name="borrows",
                to="backend.user",
            ),
        ),
        migrations.AlterField(
            model_name="circulation",
            name="member",
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name="circulations",
                to="backend.user",
            ),
        ),
        migrations.RunPython(_swap_member_fk_to_user, _swap_member_fk_to_member),
    ]
