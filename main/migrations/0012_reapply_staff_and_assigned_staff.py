# main/migrations/00XX_reapply_staff_and_assigned_staff.py
# (Replace XX with the actual migration number generated, e.g., 0012)

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings # Needed to reference AUTH_USER_MODEL

def reapply_staff_and_assigned_staff_sql(apps, schema_editor):
    """
    Manually executes SQL to create the main_staffmember table and add
    the assigned_staff_id column to main_guestrequest, along with their
    respective foreign key constraints.
    Uses IF NOT EXISTS and DO $$ BEGIN ... EXCEPTION blocks for idempotency.
    """
    # Get the actual table names, which include the app prefix (e.g., "main_staffmember")
    staff_member_table = schema_editor.connection.ops.quote_name('main_staffmember')
    guest_request_table = schema_editor.connection.ops.quote_name('main_guestrequest')
    auth_user_table = schema_editor.connection.ops.quote_name(settings.AUTH_USER_MODEL._meta.db_table)
    main_hotel_table = schema_editor.connection.ops.quote_name('main_hotel')

    with schema_editor.connection.cursor() as cursor:
        # --- 1. Create main_staffmember table if it doesn't exist ---
        # Using "serial" for ID for auto-incrementing primary key in PostgreSQL
        # Ensure column types and NULL/NOT NULL match your models.py
        create_staff_member_sql = f"""
        CREATE TABLE IF NOT EXISTS {staff_member_table} (
            "id" serial NOT NULL PRIMARY KEY,
            "user_id" integer NOT NULL UNIQUE,
            "hotel_id" integer NOT NULL,
            "category" varchar(50) NOT NULL
        );
        """
        cursor.execute(create_staff_member_sql)

        # --- 2. Add foreign key constraints to main_staffmember table if they don't exist ---
        # Use DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN null; END $$; for idempotency
        add_staff_member_fks_sql = f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'main_staffmember_user_id_fkey') THEN
                ALTER TABLE {staff_member_table} ADD CONSTRAINT "main_staffmember_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES {auth_user_table} ("id") DEFERRABLE INITIALLY DEFERRED;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'main_staffmember_hotel_id_fkey') THEN
                ALTER TABLE {staff_member_table} ADD CONSTRAINT "main_staffmember_hotel_id_fkey" FOREIGN KEY ("hotel_id") REFERENCES {main_hotel_table} ("id") DEFERRABLE INITIALLY DEFERRED;
            END IF;
        EXCEPTION
            WHEN duplicate_object THEN null; -- Ignore if constraint already exists
        END $$;
        """
        cursor.execute(add_staff_member_fks_sql)

        # --- 3. Add assigned_staff_id column to main_guestrequest if it doesn't exist ---
        # Use DO $$ BEGIN ... EXCEPTION WHEN duplicate_column THEN null; END $$; for idempotency
        # This column is nullable as per your model (null=True)
        add_assigned_staff_column_sql = f"""
        DO $$ BEGIN
            ALTER TABLE {guest_request_table} ADD COLUMN "assigned_staff_id" integer NULL;
        EXCEPTION
            WHEN duplicate_column THEN null; -- Ignore if column already exists
        END $$;
        """
        cursor.execute(add_assigned_staff_column_sql)

        # --- 4. Add foreign key constraint for assigned_staff_id if it doesn't exist ---
        add_assigned_staff_fk_sql = f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'main_guestrequest_assigned_staff_id_fkey') THEN
                ALTER TABLE {guest_request_table} ADD CONSTRAINT "main_guestrequest_assigned_staff_id_fkey" FOREIGN KEY ("assigned_staff_id") REFERENCES {staff_member_table} ("id") DEFERRABLE INITIALLY DEFERRED;
            END IF;
        EXCEPTION
            WHEN duplicate_object THEN null; -- Ignore if constraint already exists
        END $$;
        """
        cursor.execute(add_assigned_staff_fk_sql)


class Migration(migrations.Migration):

    initial = False # Set to False as this is not the first migration for the app

    dependencies = [
        # This dependency must be your *latest previous* migration for the 'main' app.
        # Based on your previous logs, this is likely 0011.
        ('main', '0011_alter_guestroomassignment_room_number_and_more'),
    ]

    operations = [
        # This operation will run the custom SQL function
        # migrations.RunPython.noop is the reverse function, meaning it does nothing on reverse migration.
        migrations.RunPython(reapply_staff_and_assigned_staff_sql, migrations.RunPython.noop),

        # These AddField and CreateModel operations are included to keep Django's
        # internal migration state consistent. They will effectively be "faked"
        # by Django because the RunPython operation already created the schema.
        # This is necessary to satisfy Django's migration tracker.
        migrations.AddField(
            model_name='guestrequest',
            name='assigned_staff',
            field=models.ForeignKey(blank=True, help_text='The staff member assigned to handle this request.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_requests', to='main.staffmember'),
        ),
        migrations.CreateModel(
            name='StaffMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('housekeeping', 'Housekeeping'), ('maintenance', 'Maintenance'), ('concierge', 'Concierge'), ('front_desk', 'Front Desk'), ('room_service', 'Room Service'), ('general_inquiry', 'General Inquiry'), ('amenity_request', 'Amenity Request'), ('general', 'General/All')], default='general', help_text='Category of staff member, defines types of requests they can handle.', max_length=50)),
                ('hotel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='staff_members', to='main.hotel')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='staff_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Staff Member',
                'verbose_name_plural': 'Staff Members',
                'ordering': ['user__username'],
            },
        ),
    ]
