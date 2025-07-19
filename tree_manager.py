#!/usr/bin/env python3
# tree_manager_cli.py
# A DYNAMIC menu-driven script to manage a family tree in a Neo4j database,
# with database selection and mandatory field handling.

from neo4j import GraphDatabase, exceptions
import os
import getpass

# --- Configuration ---
# Properties that are managed by the script and not directly editable by the user.
MANAGED_PROPERTIES = ['id', 'created_at']
# Add 'lastName' to the default keys
DEFAULT_KEYS = ['firstName', 'lastName', 'gender', 'dob', 'dod']
# Make 'lastName' mandatory by default
DEFAULT_MANDATORY_KEYS = ['firstName', 'lastName', 'gender', 'dob']

class FamilyTreeManager:
    """Manages all database operations for the family tree on a specific database."""

    def __init__(self, driver, db_name):
        self.driver = driver
        self.db_name = db_name
        self._ensure_schema_node_exists()
        print(f"\n✅ Successfully connected to database: '{self.db_name}'")

    def _ensure_schema_node_exists(self):
        """
        Ensures a :Schema node exists. It only sets default values upon creation.
        It will NOT overwrite existing schema settings on subsequent runs.
        """
        query = """
        MERGE (s:Schema {id: "person_schema"})
        ON CREATE SET s.keys = $default_keys, s.mandatory_keys = $default_mandatory_keys
        """
        self.run_query(query, default_keys=DEFAULT_KEYS, default_mandatory_keys=DEFAULT_MANDATORY_KEYS)


    def run_query(self, query, **params):
        """Helper to run queries against the selected database."""
        with self.driver.session(database=self.db_name) as session:
            return list(session.run(query, **params))

    def get_person_schema(self):
        """Gets all property keys from the :Schema node."""
        query = "MATCH (s:Schema {id: 'person_schema'}) RETURN s.keys AS schema"
        result = self.run_query(query)
        return result[0]['schema'] if result and result[0]['schema'] is not None else DEFAULT_KEYS

    def get_mandatory_keys(self):
        """Gets the list of mandatory property keys from the :Schema node."""
        query = "MATCH (s:Schema {id: 'person_schema'}) RETURN s.mandatory_keys AS mandatory"
        result = self.run_query(query)
        return result[0]['mandatory'] if result and result[0]['mandatory'] is not None else DEFAULT_MANDATORY_KEYS

    def add_person(self, person_id, properties):
        """Adds a new Person node using a dictionary of properties."""
        # Removed hardcoded lastName
        query = """
        MERGE (p:Person {id: $person_id})
        ON CREATE SET
            p.created_at = timestamp()
        SET p += $properties
        RETURN p
        """
        self.run_query(query, person_id=person_id, properties=properties)
        print(f"-> Successfully added/updated Person with ID: {person_id}")

    def update_person(self, person_id, props_to_set, props_to_remove):
        """Updates a person by setting some properties and removing others."""
        if not props_to_set and not props_to_remove:
            print("-> No changes to apply.")
            return

        set_clause = "SET p += $props_to_set" if props_to_set else ""
        remove_clause = ""
        if props_to_remove:
            remove_clause = "REMOVE " + ", ".join([f"p.`{prop}`" for prop in props_to_remove])
        
        query = f"MATCH (p:Person {{id: $id}}) {set_clause} {remove_clause}"
        self.run_query(query, id=person_id, props_to_set=props_to_set)
        print(f"-> Successfully updated Person with ID: {person_id}")

    def find_person(self, person_id):
        query = "MATCH (p:Person {id: $person_id}) RETURN p"
        result = self.run_query(query, person_id=person_id)
        return result[0]['p'] if result else None

    def find_relatives(self, person_id, relationship_pattern):
        query = f"MATCH (p:Person {{id: $person_id}}){relationship_pattern}(relative:Person) RETURN relative"
        results = self.run_query(query, person_id=person_id)
        return [record['relative'] for record in results]
        
    def list_all_persons(self):
        query = "MATCH (p:Person) RETURN p.id AS id, p.firstName AS firstName, p.lastName AS lastName ORDER BY p.id"
        results = self.run_query(query)
        return [dict(record) for record in results]

    def delete_person(self, person_id):
        query = "MATCH (p:Person {id: $person_id}) DETACH DELETE p"
        self.run_query(query, person_id=person_id)
        print(f"-> Successfully deleted Person with ID: {person_id}")
    
    def add_relationship(self, id1, id2, rel_type):
        valid_rels = ["CHILD_OF", "SPOUSE_OF"]
        if rel_type.upper() not in valid_rels:
            print(f"❌ Error: Invalid relationship type. Use one of: {valid_rels}.")
            return
        query = f"MATCH (a:Person {{id: $id1}}), (b:Person {{id: $id2}}) MERGE (a)-[r:{rel_type.upper()}]->(b)"
        self.run_query(query, id1=id1, id2=id2)
        print(f"-> Successfully linked {id1} and {id2} with relationship: {rel_type.upper()}")

    def add_property_key(self, key, is_mandatory, default_value=""):
        """Adds a new property key to the schema and to all existing nodes."""
        # Add to the main 'keys' list
        self.run_query("MATCH (s:Schema {id: 'person_schema'}) WHERE NOT $key IN s.keys SET s.keys = s.keys + $key", key=key)
        
        # If mandatory, add to the 'mandatory_keys' list
        if is_mandatory:
            self.run_query("MATCH (s:Schema {id: 'person_schema'}) WHERE NOT $key IN s.mandatory_keys SET s.mandatory_keys = s.mandatory_keys + $key", key=key)
        
        # Update existing Person nodes with the default value
        self.run_query(f"MATCH (p:Person) SET p.`{key}` = $default_value", default_value=default_value)
        print(f"-> Added property '{key}' to schema. Mandatory: {is_mandatory}")

    def rename_property_key(self, old_key, new_key):
        """Renames a property key in the schema and on all existing nodes."""
        # Rename in main keys list
        all_keys = self.get_person_schema()
        if old_key in all_keys:
            new_all_keys = [new_key if k == old_key else k for k in all_keys]
            self.run_query("MATCH (s:Schema {id:'person_schema'}) SET s.keys = $keys", keys=new_all_keys)

        # Rename in mandatory keys list if present
        mandatory_keys = self.get_mandatory_keys()
        if old_key in mandatory_keys:
            new_mandatory_keys = [new_key if k == old_key else k for k in mandatory_keys]
            self.run_query("MATCH (s:Schema {id:'person_schema'}) SET s.mandatory_keys = $keys", keys=new_mandatory_keys)

        # Update the actual nodes
        self.run_query(f"MATCH (p:Person) WHERE p.`{old_key}` IS NOT NULL SET p.`{new_key}` = p.`{old_key}` REMOVE p.`{old_key}`")
        print(f"-> Renamed property '{old_key}' to '{new_key}' for all applicable nodes.")

    def delete_property_key(self, key):
        """Deletes a property key from the schema and from all existing nodes."""
        # Remove from both lists in the schema
        self.run_query("MATCH (s:Schema {id: 'person_schema'}) SET s.keys = [k IN s.keys WHERE k <> $key], s.mandatory_keys = [mk IN s.mandatory_keys WHERE mk <> $key]", key=key)
        
        # Remove from the nodes
        self.run_query(f"MATCH (p:Person) REMOVE p.`{key}`")
        print(f"-> Deleted property '{key}' from schema and all Person nodes.")


# --- User Interface Functions ---

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_input(prompt, required=True):
    while True:
        value = input(f"{prompt}: ").strip()
        if value or not required:
            return value
        print("This field is required. Please enter a value.")

def main_menu():
    print("\n🌳 Maliyakkal Family Tree Manager (Dynamic) 🌳")
    print("--------------------------------------")
    print("1. Add a New Person")
    print("2. Modify an Existing Person")
    print("3. Delete a Person")
    print("4. Add a Relationship")
    print("5. Configure Property Keys")
    print("6. List All Property Keys")
    print("7. List a Person's Info")
    print("8. List All Persons")
    print("0. Exit")
    print("--------------------------------------")
    return get_input("Choose an option")

def add_person_menu(tree):
    print("\n--- Add a New Person ---")
    person_id = get_input("Unique ID (e.g., gen2_04)")
    schema = tree.get_person_schema()
    mandatory_keys = tree.get_mandatory_keys()
    properties = {}
    print("Please provide the following details:")
    for prop in schema:
        is_req = prop in mandatory_keys
        prompt = f"{prop}{' (mandatory)' if is_req else ''}"
        value = get_input(prompt, required=is_req)
        if value:  # Only add property if a value was entered
            properties[prop] = value
    tree.add_person(person_id, properties)

def modify_person_menu(tree):
    person_id = get_input("Enter the ID of the person to modify")
    person = tree.find_person(person_id)
    if not person:
        print("❌ Error: Person not found.")
        return
    print("\n--- Modifying Person ---")
    print("Enter new values below (or press Enter to keep the current value).")
    
    schema = tree.get_person_schema()
    mandatory_keys = tree.get_mandatory_keys()
    props_to_set = {}
    props_to_remove = []

    for prop in schema:
        is_req = prop in mandatory_keys
        current_value = person.get(prop, "")
        prompt = f"{prop} (currently '{current_value}'){' (mandatory)' if is_req else ''}"
        new_val = get_input(prompt, required=is_req)

        if new_val != current_value:
            if new_val:
                props_to_set[prop] = new_val
            elif not is_req: # Can only clear non-mandatory fields
                props_to_remove.append(prop)
    
    tree.update_person(person_id, props_to_set, props_to_remove)

def list_keys_menu(tree):
    print("\n--- Current Editable Property Keys ---")
    keys = tree.get_person_schema()
    mandatory_keys = tree.get_mandatory_keys()
    if keys:
        for key in keys:
            print(f"  - {key} {'(mandatory)' if key in mandatory_keys else ''}")
        print("------------------------------------")
        print("(Managed keys like 'id' and 'created_at' are not listed.)")
    else:
        print("-> Schema not found or is empty.")

def list_person_info_menu(tree):
    person_id = get_input("Enter the ID of the person to list")
    person = tree.find_person(person_id)
    if not person:
        print("❌ Error: Person not found.")
        return
    clear_screen()
    print(f"\n--- Information for {person.get('firstName', '')} ({person_id}) ---")
    print("\nProperties:")
    for key, value in sorted(person.items()):
        print(f"  - {key}: {value}")
    parents = tree.find_relatives(person_id, "-[:CHILD_OF]->")
    if parents:
        print("\nParents:")
        for p in parents: print(f"  - {p.get('firstName', 'N/A')} (ID: {p.get('id')})")
    spouses = tree.find_relatives(person_id, "-[:SPOUSE_OF]-")
    if spouses:
        print("\nSpouses:")
        for s in spouses: print(f"  - {s.get('firstName', 'N/A')} (ID: {s.get('id')})")
    children = tree.find_relatives(person_id, "<-[:CHILD_OF]-")
    if children:
        print("\nChildren:")
        for c in children: print(f"  - {c.get('firstName', 'N/A')} (ID: {c.get('id')})")
    print("-------------------------------------------------")

def list_all_persons_menu(tree):
    """Lists all people in the database in a table format."""
    print("\n--- All Persons in Family Tree ---")
    persons = tree.list_all_persons()
    if not persons:
        print("-> No people found in the database.")
        return

    # Safely calculate max column widths, defaulting to an empty string if a value is None
    max_id = max((len(p.get('id') or '') for p in persons), default=2)
    max_first = max((len(p.get('firstName') or '') for p in persons), default=9)
    max_last = max((len(p.get('lastName') or '') for p in persons), default=8)

    header = f"{'ID'.ljust(max_id)} | {'First Name'.ljust(max_first)} | {'Last Name'.ljust(max_last)}"
    print(header)
    print(f"{'-' * max_id}-+-{'-' * max_first}-+-{'-' * max_last}")

    for person in persons:
        # Safely get values, defaulting to 'N/A' if None
        id_val = person.get('id') or 'N/A'
        first_val = person.get('firstName') or 'N/A'
        last_val = person.get('lastName') or 'N/A'
        print(f"{id_val.ljust(max_id)} | {first_val.ljust(max_first)} | {last_val.ljust(max_last)}")
    print("-" * len(header))

def relationship_menu(tree):
    print("\n--- Add a Relationship ---")
    id1 = get_input("Enter the first Person's ID")
    id2 = get_input("Enter the second Person's ID")
    rel_type = get_input("Relationship Type (CHILD_OF or SPOUSE_OF)")
    tree.add_relationship(id1, id2, rel_type)

def config_menu(tree):
    while True:
        clear_screen()
        print("\n--- Configure Property Keys ---")
        print("1. Add a new property")
        print("2. Rename an existing property")
        print("3. Delete a property")
        print("4. Back to Main Menu")
        print("---------------------------------")
        choice = get_input("Choose an option")
        if choice == '1':
            key = get_input("Enter new property name")
            if key in MANAGED_PROPERTIES:
                print(f"❌ Error: '{key}' is a managed property.")
                get_input("Press Enter...", required=False)
                continue
            is_mandatory = get_input("Is this property mandatory? (yes/no)", required=True).lower() == 'yes'
            default = get_input("Default value (can be blank)", required=False)
            tree.add_property_key(key, is_mandatory, default)
            get_input("Press Enter...", required=False)
        elif choice == '2':
            old_key = get_input("Property to rename")
            new_key = get_input("New property name")
            tree.rename_property_key(old_key, new_key)
            get_input("Press Enter...", required=False)
        elif choice == '3':
            key = get_input("Property to delete")
            if get_input(f"⚠️ Sure you want to delete '{key}'? (yes/no)").lower() == 'yes':
                tree.delete_property_key(key)
            else:
                print("-> Deletion cancelled.")
            get_input("Press Enter...", required=False)
        elif choice == '4':
            break
        else:
            print("❌ Invalid option.")
            get_input("Press Enter...", required=False)

# --- Main Startup Block ---

def connect_and_select_db():
    """Handles the initial connection and DB selection for both local and AuraDB."""
    clear_screen()
    print("--- Neo4j Database Connection ---")
    #uri = get_input("Enter Neo4j URI (e.g., neo4j+s://... or bolt://localhost:7687)")
    uri = "neo4j+s://51ac777b.databases.neo4j.io"
    #password = getpass.getpass("Enter Neo4j Password: ")
    password = "Mymxj76bqL-RFJmNWTEqprHNbeSZtTAqVFLavbY_JCw"
    driver = None
    try:
        driver = GraphDatabase.driver(uri, auth=("neo4j", password))
        driver.verify_connectivity()
        
        # Check if it's an AuraDB instance
        if ".databases.neo4j.io" in uri:
            print("\n✅ AuraDB connection successful.")
            return driver, "neo4j" # Aura's default DB is 'neo4j'
        else:
            # It's a local instance, so list databases
            records, _, _ = driver.execute_query("SHOW DATABASES")
            db_names = [rec["name"] for rec in records if rec["name"] not in ["system", "neo4j"]]
            
            if not db_names:
                print("\n❌ No user-created databases found. Please create one in Neo4j Desktop first.")
                return None, None

            print("\nAvailable Databases:")
            for i, name in enumerate(db_names):
                print(f"  {i + 1}. {name}")
            
            while True:
                choice = get_input("\nSelect a database (number): ")
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(db_names):
                        return driver, db_names[index]
                    else:
                        print("❌ Invalid number. Please try again.")
                except ValueError:
                    print("❌ Please enter a number.")

    except exceptions.AuthError:
        print("\n❌ Authentication failed. Please check your password and try again.")
        return None, None
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        return None, None

if __name__ == "__main__":
    driver, db_name = connect_and_select_db()
    manager = None

    if driver and db_name:
        try:
            manager = FamilyTreeManager(driver, db_name)
            while True:
                clear_screen()
                choice = main_menu()
                if choice == '1': add_person_menu(manager)
                elif choice == '2': modify_person_menu(manager)
                elif choice == '3':
                    person_id = get_input("Enter ID of person to delete")
                    if get_input(f"⚠️ Sure? (yes/no)").lower() == 'yes':
                        manager.delete_person(person_id)
                elif choice == '4': relationship_menu(manager)
                elif choice == '5': config_menu(manager)
                elif choice == '6': list_keys_menu(manager)
                elif choice == '7': list_person_info_menu(manager)
                elif choice == '8': list_all_persons_menu(manager)
                elif choice == '0': break
                else: print("❌ Invalid option.")
                
                get_input("\nPress Enter to return to the menu...", required=False)
        except Exception as e:
            print(f"\n❌ An unexpected error occurred: {e}")
        finally:
            if driver:
                driver.close()
                print("\n✅ Database connection closed.")

