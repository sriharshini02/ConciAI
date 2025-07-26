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
    # Get the actual model classes from the 'apps' registry
    User = apps.get_model(settings.AUTH_USER_MODEL.split('.')[0], settings.AUTH_USER_MODEL.split('.')[1])
    Hotel = apps.get_model('main', 'Hotel') # Assuming Hotel is in 'main' app

    # Get the actual table names, which include the app prefix (e.g., "main_staffmember")
    staff_member_table = schema_editor.connection.ops.quote_name('main_staffmember')
    guest_request_table = schema_editor.connection.ops.quote_name('main_guestrequest')
    
    # CORRECTED: Get db_table from the actual model class
    auth_user_table = schema_editor.connection.ops.quote_name(User._meta.db_table)
    main_hotel_table = schema_editor.connection.ops.quote_name(Hotel._meta.db_table)

    with schema_editor.connection.cursor() as cursor:
        # --- 1. Create main_staffmember table if it doesn't exist ---
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

    initial = False

    dependencies = [
        ('main', '0011_alter_guestroomassignment_room_number_and_more'),
    ]

    operations = [
        # Only keep the RunPython operation.
        # The AddField and CreateModel operations are now redundant and cause DuplicateColumn errors.
        migrations.RunPython(reapply_staff_and_assigned_staff_sql, migrations.RunPython.noop),
    ]
