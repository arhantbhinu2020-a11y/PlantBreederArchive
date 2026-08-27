import pandas as pd
from pathlib import Path
from sqlalchemy.orm import Session
from db import engine, Plot, Management, Record, Variable, Image


def read_excel_file(file_path):
    data = pd.read_excel(file_path)

    print("Columns found:")
    for column in data.columns:
        print(f"- {column}")
    print("\nData:")
    print(data)
    return(data)

def validate_excel_file(data):
    required_columns = {"Plot Name", "Date", "Crop"}

    missing_columns = required_columns - set(data.columns)

    if missing_columns:
        print("\nERROR: Missing required columns:")
        for column in missing_columns:
            print(f"- {column}")
        return False

    if data.empty:
        print("\nERROR: Excel file contains no data.")
        return False

    if data["Plot Name"].isna().any():
        print("\nERROR: One or more rows are missing a Plot Name.")
        return False

    if data["Date"].isna().any():
        print("\nERROR: One or more rows are missing a Date.")
        return False

    return True

def find_variables(data):
    required_columns = {"Plot Name", "Date", "Crop"}

    variables = [
        column for column in data.columns
        if column not in required_columns
    ]

    print("\nVariables found:")
    for variable in variables:
        print(f"- {variable}")

    return variables

def get_row_data(row, variables):
    management_data = {
        "plot_name": row["Plot Name"],
        "date": row["Date"],
        "crop": row["Crop"]
    }

    variable_data = {}

    for variable in variables:
        variable_data[variable] = row[variable]

    return management_data, variable_data

def test_database_connection():
    with Session(engine) as session:
        plots = session.query(Plot).all()

        print("\nPlots currently in database:")
        for plot in plots:
            print(f"-{plot.name}")

def find_plot(plot_name):
    with Session(engine) as session:
        plot = session.query(Plot).filter(Plot.name == plot_name).first()

        if plot is None:
            print(f"\nPlot '{plot_name}' was not found in the database.")
            return None

        print(f"\nExcel plot '{plot_name}' matched database plot:")
        print(f"Name: {plot.name}")
        print(f"ID: {plot.id}")

        return plot.id

def create_management(plot_id, management_data):
    with Session(engine) as session:
        management_date = management_data["date"].date()

        existing_management = session.query(Management).filter(
            Management.plotid == plot_id,
            Management.date == management_date
        ).first()

        if existing_management is not None:
            print("\nManagement entry already exists:")
            print(f"Name: {existing_management.name}")
            print(f"ID: {existing_management.id}")

            return existing_management.id, False

        management = Management(
            name=f"{management_data['plot_name']}_{management_date}",
            date=management_date,
            goal=management_data["crop"],
            plotid=plot_id
        )

        session.add(management)
        session.commit()

        print("\nManagement entry created:")
        print(f"Name: {management.name}")
        print(f"ID: {management.id}")
        print(f"Plot ID: {management.plotid}")

        return management.id, True


def find_or_create_variable(variable_name):
    with Session(engine) as session:
        variable = session.query(Variable).filter(
            Variable.name == variable_name
        ).first()

        if variable is None:
            variable = Variable(name=variable_name)
            session.add(variable)
            session.commit()

            print(f"\nCreated new variable: {variable.name}")
        else:
            print(f"\nFound existing variable: {variable.name}")

        return variable.id

def create_record(management_id, variable_id, value):
    with Session(engine) as session:
        existing_record = session.query(Record).filter(
            Record.managementid == management_id,
            Record.variableid == variable_id
        ).first()

        if existing_record is not None:
            print("\nRecord already exists:")
            print(f"Management ID: {management_id}")
            print(f"Variable ID: {variable_id}")
            print(f"Value: {existing_record.ground_truth}")

            return existing_record.id, False

        record = Record(
            ground_truth=float(value),
            managementid=management_id,
            variableid=variable_id
        )

        session.add(record)
        session.commit()

        print("\nRecord created:")
        print(f"Management ID: {management_id}")
        print(f"Variable ID: {variable_id}")
        print(f"Value: {value}")

        return record.id, True

def import_images(image_folder, import_stats):
    image_folder = Path(image_folder)

    for image_path in image_folder.iterdir():
        if not image_path.is_file():
            continue

        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue

        parts = image_path.stem.split("_")

        if len(parts) < 4:
            print(f"Skipping image with invalid filename: {image_path.name}")
            import_stats["images_skipped"] += 1
            continue

        plot_name = "_".join(parts[:-1])
        image_date = parts[-1]

        with Session(engine) as session:
            plot = session.query(Plot).filter(
                Plot.name == plot_name
            ).first()

            if plot is None:
                print(f"\nImage skipped: plot '{plot_name}' not found.")
                continue

            existing_image = session.query(Image).filter(
                Image.url == image_path.name,
                Image.plotid == plot.id
            ).first()

            if existing_image is not None:
                print(f"\nImage already exists: {image_path.name}")
                import_stats["images_existing"] += 1
                continue

            image = Image(
                url=image_path.name,
                plotid=plot.id
            )

            session.add(image)
            session.commit()

            management = session.query(Management).filter(
                Management.plotid == plot.id,
                Management.date == pd.to_datetime(image_date).date()
            ).first()

            if management is None:
                print(
                    f"\nImage skipped: no management entry found for "
                    f"{plot.name} on {image_date}."
                )

                session.delete(image)
                session.commit()

                import_stats["images_skipped"] += 1
                continue

            management.imageid = image.id
            session.commit()

            import_stats["images_imported"] += 1

            print(f"\nImage imported: {image_path.name}")
            print(f"Plot: {plot.name}")
            print(f"Image ID: {image.id}")

def validate_image_folder(image_folder):
    image_folder = Path(image_folder)

    if not image_folder.exists():
        print("\nERROR: Image folder does not exist.")
        return False

    if not image_folder.is_dir():
        print("\nERROR: The selected path is not a folder.")
        return False

    return True
def validate_images_against_excel(data, image_folder):
    image_folder = Path(image_folder)

    expected_images = set()

    for _, row in data.iterrows():
        plot_name = str(row["Plot Name"])
        date = pd.to_datetime(row["Date"]).date()

        expected_images.add(f"{plot_name}_{date}")

    found_images = set()

    for image_path in image_folder.iterdir():
        if not image_path.is_file():
            continue

        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue

        found_images.add(image_path.stem)

    missing_images = expected_images - found_images
    unexpected_images = found_images - expected_images

    if missing_images:
        print("\nWARNING - Images missing from folder:")
        for image in sorted(missing_images):
            print(f"- {image}")

    if unexpected_images:
        print("\nWARNING - Images found that are not in the Excel file:")
        for image in sorted(unexpected_images):
            print(f"- {image}")

    if not missing_images and not unexpected_images:
        print("\nImage validation passed.")


def process_row(row, variables, import_stats):
    management_data, variable_data = get_row_data(row, variables)

    print("\n" + "=" * 40)
    print(f"Processing plot: {management_data['plot_name']}")

    plot_id = find_plot(management_data["plot_name"])

    if plot_id is None:
        print("Skipping row because the plot was not found.")
        import_stats["plots_skipped"] += 1
        return
    import_stats["plots_matched"] += 1

    management_id, created = create_management(
        plot_id,
        management_data
    )

    if created:
        import_stats["managements_created"] += 1
    else:
        import_stats["managements_existing"] += 1

    for variable, value in variable_data.items():
        if pd.isna(value):
            print(f"Skipping {variable}: no value provided.")
            continue
        variable_id = find_or_create_variable(variable)
        record_id, created = create_record(
            management_id,
            variable_id,
            value
        )

        if created:
            import_stats["records_created"] += 1
        else:
            import_stats["records_existing"] += 1

import_stats = {
    "rows_processed": 0,
    "plots_matched": 0,
    "plots_skipped": 0,
    "managements_created": 0,
    "managements_existing": 0,
    "records_created": 0,
    "records_existing": 0,
    "images_imported": 0,
    "images_existing": 0,
    "images_skipped": 0
}

if __name__ == "__main__":
    file_path = input("Enter the Excel file path: ").strip("'\"")
    data = read_excel_file(file_path)

    if not validate_excel_file(data):
        exit()

    variables = find_variables(data)

    for _, row in data.iterrows():
        process_row(row, variables, import_stats)
        import_stats["rows_processed"] += 1

    image_folder = input("\nEnter the image folder path: ").strip("'\"")

    if validate_image_folder(image_folder):
        validate_images_against_excel(data, image_folder)
        import_images(image_folder, import_stats)

    print("\n" + "=" * 40)
    print("IMPORT COMPLETE")
    print("=" * 40)
    print(f"Excel rows processed: {import_stats['rows_processed']}")
    print(f"Plots matched: {import_stats['plots_matched']}")
    print(f"Plots skipped: {import_stats['plots_skipped']}")
    print(f"Records created: {import_stats['records_created']}")
    print(f"Records already existing: {import_stats['records_existing']}")
    print(f"Images imported and linked: {import_stats['images_imported']}")
    print(f"Images already existing: {import_stats['images_existing']}")
    print(f"Images skipped: {import_stats['images_skipped']}")
    print(f"Managements created: {import_stats['managements_created']}")
    print(f"Managements already existing: {import_stats['managements_existing']}")