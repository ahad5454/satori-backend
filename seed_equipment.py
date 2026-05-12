import json
import os
import sys

# Add the current directory to sys.path so that 'app' module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app.models.equipment_consumables import EquipmentCategory, EquipmentItem

def seed_equipment():
    # Path to the seed file relative to the script directory
    seed_file_path = os.path.join(os.path.dirname(__file__), '..', 'equipment_seed.json')
    
    with open(seed_file_path, 'r') as f:
        data = json.load(f)

    db = SessionLocal()
    
    try:
        print("Clearing existing equipment categories and items...")
        db.query(EquipmentItem).delete()
        db.query(EquipmentCategory).delete()
        db.commit()
        
        print("Seeding new data...")
        for section_key, categories in data.items():
            if "SECTION 1" in section_key:
                section_val = 1
            elif "SECTION 2" in section_key:
                section_val = 2
            else:
                print(f"Unknown section: {section_key}, skipping.")
                continue
                
            for cat_name, items in categories.items():
                category = EquipmentCategory(name=cat_name, section=section_val)
                db.add(category)
                db.flush() # Get the generated ID
                
                for item_data in items:
                    item = EquipmentItem(
                        category_id=category.id,
                        description=item_data["name"],
                        unit=item_data["unit"],
                        unit_cost=item_data["unit_cost"]
                    )
                    db.add(item)
                    
        db.commit()
        print("Successfully seeded equipment data.")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_equipment()
