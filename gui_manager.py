#!/usr/bin/env python3
# gui_manager.py
# A graphical user interface for managing the Maliyakkal Family Tree in Neo4j.

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from neo4j import GraphDatabase, exceptions

# --- Main Application Class ---
class FamilyTreeApp(tk.Tk):
    """The main application window and logic."""

    def __init__(self):
        super().__init__()
        self.title("Maliyakkal Family Tree GUI Manager")
        self.geometry("800x600")

        self.driver = None
        self.db_name = None
        self.current_person_id = None
        
        # --- State management for refreshing the view ---
        self.view_mode = 'generation' # Can be 'generation' or 'children'
        self.view_context_id = 1 # Stores gen number or parent ID
        self.history = [] # To store navigation history

        # --- Style ---
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TLabel", padding=6, font=("Helvetica", 10))
        style.configure("TButton", padding=6, font=("Helvetica", 10, "bold"))
        style.configure("Header.TLabel", font=("Helvetica", 14, "bold"))
        style.configure("Treeview", rowheight=25, font=("Helvetica", 10))
        style.configure("Treeview.Heading", font=("Helvetica", 11, "bold"))

        # --- Initial connection screen ---
        self.show_connection_screen()

        # --- Bring window to front and set focus ---
        self.lift()
        self.attributes('-topmost', True)
        self.after_idle(self.attributes, '-topmost', False)
        self.focus_force()
        self.after_idle(self.password_entry.focus_set)

    def show_connection_screen(self):
        """Displays the initial screen to connect to the database."""
        for widget in self.winfo_children():
            widget.destroy()

        self.conn_frame = ttk.Frame(self, padding="20")
        self.conn_frame.pack(expand=True)

        ttk.Label(self.conn_frame, text="Connect to Neo4j Database", style="Header.TLabel").pack(pady=10)
        
        ttk.Label(self.conn_frame, text="Database URI:").pack(pady=5)
        self.uri_entry = ttk.Entry(self.conn_frame, width=40)
        self.uri_entry.insert(0, "neo4j+s://your-aura-instance.databases.neo4j.io")
        self.uri_entry.pack()

        ttk.Label(self.conn_frame, text="Password:").pack(pady=5)
        self.password_entry = ttk.Entry(self.conn_frame, show="*", width=40)
        self.password_entry.pack()
        # Bind the Enter key to the connect button
        self.password_entry.bind('<Return>', lambda event: self.connect_to_db())

        self.connect_button = ttk.Button(self.conn_frame, text="Connect", command=self.connect_to_db)
        self.connect_button.pack(pady=20)

    def connect_to_db(self):
        """Handles the database connection and fetches database names."""
        uri = self.uri_entry.get()
        password = self.password_entry.get()
        user = "neo4j"

        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()

            # --- Smart Connection Logic ---
            # If it's an AuraDB URI, skip database selection.
            if ".databases.neo4j.io" in uri:
                self.db_name = "neo4j" # AuraDB's default database
                messagebox.showinfo("Connection Successful", f"Connected to AuraDB instance.\nUsing default database: '{self.db_name}'")
                self.initialize_main_app()
            else: # For local instances, show the database list
                with self.driver as temp_driver:
                    records, _, _ = temp_driver.execute_query("SHOW DATABASES")
                    db_names = [rec["name"] for rec in records if rec["name"] not in ["system", "neo4j"]]
                
                if not db_names:
                    messagebox.showwarning("No Databases Found", "Could not find any user-created databases on this local instance.")
                    return
                self.show_db_selection(db_names)

        except exceptions.AuthError:
            messagebox.showerror("Connection Failed", "Authentication failed. Please check your password.")
        except Exception as e:
            messagebox.showerror("Connection Failed", f"An error occurred: {e}")

    def show_db_selection(self, db_names):
        """Shows a screen to select the target database."""
        for widget in self.winfo_children():
            widget.destroy()

        self.db_frame = ttk.Frame(self, padding="20")
        self.db_frame.pack(expand=True)

        ttk.Label(self.db_frame, text="Select a Database", style="Header.TLabel").pack(pady=10)
        
        self.db_var = tk.StringVar()
        self.db_combobox = ttk.Combobox(self.db_frame, textvariable=self.db_var, values=db_names, state="readonly", width=30)
        if db_names:
            self.db_combobox.set(db_names[0])
        self.db_combobox.pack(pady=10)
        self.db_combobox.focus()
        self.db_combobox.bind('<Return>', lambda event: self.initialize_main_app())


        ttk.Button(self.db_frame, text="Select", command=self.initialize_main_app).pack(pady=10)

    def initialize_main_app(self):
        """Sets up the main application interface after connection."""
        if not self.db_name: # This will be set for local DBs on button press
            self.db_name = self.db_var.get()
        
        if not self.db_name:
            messagebox.showwarning("No Database", "Please select a database to continue.")
            return
            
        for widget in self.winfo_children():
            widget.destroy()
        
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        self.current_selection_label = ttk.Label(header_frame, text="Current Selection: None", font=("Helvetica", 11, "italic"))
        self.current_selection_label.pack(side="left")
        
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        
        self.tree = ttk.Treeview(tree_frame, columns=("ID", "Name", "DOB"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("DOB", text="Date of Birth")
        self.tree.column("ID", width=150)
        self.tree.column("Name", width=250)
        self.tree.column("DOB", width=150)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.tree.bind("<<TreeviewSelect>>", self.on_person_select)
        # Bind double-click to view children
        self.tree.bind("<Double-1>", self.on_double_click)

        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        
        self.add_child_button = ttk.Button(action_frame, text="Add Child", command=self.add_child, state="disabled")
        self.add_child_button.pack(side="left", padx=5)

        self.add_sibling_button = ttk.Button(action_frame, text="Add Sibling", command=self.add_sibling, state="disabled")
        self.add_sibling_button.pack(side="left", padx=5)
        
        self.add_spouse_button = ttk.Button(action_frame, text="Add Spouse", command=self.add_spouse, state="disabled")
        self.add_spouse_button.pack(side="left", padx=5)

        self.modify_button = ttk.Button(action_frame, text="Modify Person", command=self.modify_person, state="disabled")
        self.modify_button.pack(side="left", padx=5)

        self.view_children_button = ttk.Button(action_frame, text="View Children", command=self.view_children, state="disabled")
        self.view_children_button.pack(side="left", padx=5)

        self.back_button = ttk.Button(action_frame, text="Go Back", command=self.go_back, state="disabled")
        self.back_button.pack(side="right", padx=5)

        self.top_gen_button = ttk.Button(action_frame, text="Go to Top Generation", command=self.go_to_top_generation)
        self.top_gen_button.pack(side="right", padx=5)

        self.go_to_top_generation()

    def run_query(self, query, **params):
        if not self.driver or not self.db_name:
            messagebox.showerror("Error", "Database connection not available.")
            return []
        records, _, _ = self.driver.execute_query(query, params, database_=self.db_name)
        return records

    def get_schema_details(self):
        """Fetches both the full schema and the mandatory keys."""
        query = "MATCH (s:Schema {id: 'person_schema'}) RETURN s.keys AS schema, s.mandatory_keys as mandatory"
        records = self.run_query(query)
        if not records:
            messagebox.showerror("Schema Error", "Could not find the data schema in the database.")
            return None, None
        
        schema = records[0].get("schema") or []
        mandatory_keys = records[0].get("mandatory") or []
        return schema, mandatory_keys

    def _load_view(self, mode, context_id, add_to_history=True):
        """Master function to load a view and manage navigation history."""
        if add_to_history:
            self.history.append((self.view_mode, self.view_context_id))

        if mode == 'children':
            self._display_children_internal(context_id)
        else: # 'generation'
            self._display_top_gen_internal()

        self.back_button.config(state="normal" if self.history else "disabled")

    def _display_top_gen_internal(self):
        """Internal logic to display the top generation."""
        self.view_mode = 'generation'
        self.view_context_id = 1
        self.tree.delete(*self.tree.get_children())
        self.current_selection_label.config(text="Displaying Top Generation (people with no parents)")
        
        query = """
        MATCH (p:Person) 
        WHERE NOT (p)-[:CHILD_OF]->(:Person)
        RETURN p.id AS id, 
               coalesce(p.firstName, 'N/A') AS name, 
               coalesce(p.dob, 'Not Set') AS dob 
        ORDER BY p.id
        """
        people = self.run_query(query)
        
        for person in people:
            self.tree.insert("", "end", values=(person["id"], person["name"], person["dob"]))
        
        self.reset_buttons()

    def _display_children_internal(self, parent_id):
        """Internal logic to display children of a given parent ID."""
        self.view_mode = 'children'
        self.view_context_id = parent_id
        
        self.tree.delete(*self.tree.get_children())
        
        parent_name_records = self.run_query("MATCH (p:Person {id: $id}) RETURN p.firstName as name", id=parent_id)
        parent_name = parent_name_records[0]['name'] if parent_name_records else parent_id
        
        self.current_selection_label.config(text=f"Children of: {parent_name}")

        query = """
        MATCH (parent:Person {id: $parent_id})<-[:CHILD_OF]-(child:Person)
        RETURN child.id AS id, 
               coalesce(child.firstName, 'N/A') AS name, 
               coalesce(child.dob, 'Not Set') AS dob
        ORDER BY child.id
        """
        children = self.run_query(query, parent_id=parent_id)
        for child in children:
            self.tree.insert("", "end", values=(child["id"], child["name"], child["dob"]))
        
        self.reset_buttons()

    def on_person_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            self.current_person_id = None
            self.reset_buttons()
            return

        selected_item = selected_items[0]
        self.current_person_id = self.tree.item(selected_item, "values")[0]
        person_name = self.tree.item(selected_item, "values")[1]
        
        self.current_selection_label.config(text=f"Selected: {person_name} (ID: {self.current_person_id})")
        self.add_child_button.config(state="normal")
        self.add_sibling_button.config(state="normal")
        self.add_spouse_button.config(state="normal")
        self.modify_button.config(state="normal")
        self.view_children_button.config(state="normal")

    def on_double_click(self, event):
        """Handler for double-clicking a person in the tree."""
        if self.tree.selection():
            self.view_children()

    def reset_buttons(self):
        self.add_child_button.config(state="disabled")
        self.add_sibling_button.config(state="disabled")
        self.add_spouse_button.config(state="disabled")
        self.modify_button.config(state="disabled")
        self.view_children_button.config(state="disabled")
        self.current_person_id = None

    def view_children(self):
        if not self.current_person_id: return
        self._load_view('children', self.current_person_id)

    def go_to_top_generation(self):
        self.history.clear()
        self._load_view('generation', 1, add_to_history=False)

    def go_back(self):
        if not self.history:
            return
        prev_mode, prev_context_id = self.history.pop()
        self._load_view(prev_mode, prev_context_id, add_to_history=False)

    def add_child(self):
        if not self.current_person_id: return
        
        parent_gen_query = "MATCH (p:Person {id: $id}) RETURN p.genNumber AS gen"
        records = self.run_query(parent_gen_query, id=self.current_person_id)
        
        parent_gen = 1
        if records and records[0]["gen"] is not None:
            parent_gen = int(records[0]["gen"])
        
        child_gen = parent_gen + 1
        self.open_person_form("child", self.current_person_id, child_gen)

    def add_sibling(self):
        """Opens a form to add a sibling to the selected person."""
        if not self.current_person_id: return
        
        parent_query = "MATCH (p:Person {id: $id})-[:CHILD_OF]->(:Person) RETURN p.genNumber AS gen"
        records = self.run_query(parent_query, id=self.current_person_id)
        
        if not records:
            messagebox.showerror("Cannot Add Sibling", "The selected person has no parents in the database. A sibling cannot be added.")
            return
            
        sibling_gen = 1
        if records[0]["gen"] is not None:
            sibling_gen = int(records[0]["gen"])
        self.open_person_form("sibling", self.current_person_id, sibling_gen)

    def add_spouse(self):
        if not self.current_person_id: return
        
        person_gen_query = "MATCH (p:Person {id: $id}) RETURN p.genNumber AS gen"
        records = self.run_query(person_gen_query, id=self.current_person_id)
        
        spouse_gen = 1
        if records and records[0]["gen"] is not None:
            spouse_gen = int(records[0]["gen"])

        self.open_person_form("spouse", self.current_person_id, spouse_gen)

    def modify_person(self):
        """Opens a form to modify the selected person's details."""
        if not self.current_person_id: return

        person_data_query = "MATCH (p:Person {id: $id}) RETURN p"
        records = self.run_query(person_data_query, id=self.current_person_id)
        if not records:
            messagebox.showerror("Error", "Could not fetch person's data.")
            return
        person_data = dict(records[0]['p'])

        schema, mandatory_keys = self.get_schema_details()
        if schema is None: return

        dialog = PersonFormDialog(self, "Modify Person", schema, person_data.get('genNumber', 1), mandatory_keys=mandatory_keys, initial_data=person_data)
        self.wait_window(dialog)

        if dialog.result:
            updated_data = dialog.result
            
            props_to_set = {k: v for k, v in updated_data.items() if v}
            props_to_remove = [k for k, v in updated_data.items() if not v and k != 'genNumber']

            set_clause = "SET p += $props"
            remove_clause = ""
            if props_to_remove:
                remove_clause = " REMOVE " + ", ".join([f"p.`{prop}`" for prop in props_to_remove])
            
            query = f"MATCH (p:Person {{id: $id}}) {set_clause}{remove_clause}"

            self.run_query(
                query,
                id=self.current_person_id,
                props=props_to_set
            )
            messagebox.showinfo("Success", "Person's details updated successfully!")
            self.refresh_current_view()

    def open_person_form(self, relationship_type, related_person_id, gen_number):
        schema, mandatory_keys = self.get_schema_details()
        if schema is None: return
        
        dialog = PersonFormDialog(self, f"Add New {relationship_type.capitalize()}", schema, gen_number, relationship_type, related_person_id, mandatory_keys=mandatory_keys)
        self.wait_window(dialog)

        if dialog.result:
            new_person_data = {k: v for k, v in dialog.result.items() if v and k != 'id'}
            new_person_id = dialog.result.get('id')
            
            if not new_person_id:
                messagebox.showwarning("ID Required", "A unique ID could not be generated or was not provided.")
                return

            self.run_query(
                "CREATE (p:Person {id: $id}) SET p += $props",
                id=new_person_id,
                props=new_person_data
            )

            # --- Link the new person based on the relationship type ---
            if relationship_type == "child":
                spouses_query = "MATCH (p:Person {id: $id})-[:SPOUSE_OF]-(s:Person) RETURN s.id AS id"
                spouses = self.run_query(spouses_query, id=related_person_id)
                parent_ids = [related_person_id] + [s['id'] for s in spouses]
                
                for parent_id in parent_ids:
                    self.run_query(
                        "MATCH (c:Person {id: $child_id}), (p:Person {id: $parent_id}) MERGE (c)-[:CHILD_OF]->(p)",
                        child_id=new_person_id, parent_id=parent_id
                    )
            elif relationship_type == "sibling":
                parents_query = "MATCH (:Person {id: $id})-[:CHILD_OF]->(parent:Person) RETURN parent.id AS id"
                parents = self.run_query(parents_query, id=related_person_id)
                parent_ids = [p['id'] for p in parents]

                for parent_id in parent_ids:
                    self.run_query(
                        "MATCH (c:Person {id: $child_id}), (p:Person {id: $parent_id}) MERGE (c)-[:CHILD_OF]->(p)",
                        child_id=new_person_id, parent_id=parent_id
                    )
            elif relationship_type == "spouse":
                self.run_query(
                    "MATCH (p1:Person {id: $p1_id}), (p2:Person {id: $p2_id}) MERGE (p1)-[:SPOUSE_OF]-(p2)",
                    p1_id=new_person_id, p2_id=related_person_id
                )
            
            messagebox.showinfo("Success", f"{relationship_type.capitalize()} added successfully!")
            self.refresh_current_view()

    def refresh_current_view(self):
        """Refreshes the treeview based on the last viewed context."""
        self._load_view(self.view_mode, self.view_context_id, add_to_history=False)


# --- Dynamic Form Dialog ---
class PersonFormDialog(tk.Toplevel):
    """A dialog window with a dynamically generated form."""
    def __init__(self, parent, title, schema, gen_number, relationship_type=None, related_person_id=None, mandatory_keys=None, initial_data=None):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.entries = {}
        self.relationship_type = relationship_type
        self.related_person_id = related_person_id
        self.mandatory_keys = mandatory_keys or []
        
        form_frame = ttk.Frame(self, padding="20")
        form_frame.pack(expand=True)

        # Filter 'genNumber' from the schema list to avoid duplication
        form_schema = [prop for prop in schema if prop != 'genNumber']

        ttk.Label(form_frame, text="genNumber:").grid(row=0, column=0, sticky="w", pady=2)
        self.entries["genNumber"] = ttk.Entry(form_frame)
        self.entries["genNumber"].grid(row=0, column=1, sticky="ew", pady=2)
        self.entries["genNumber"].insert(0, str(gen_number))
        self.entries["genNumber"].config(state="readonly")

        row_counter = 1
        for prop in form_schema:
            is_mandatory = prop in self.mandatory_keys
            label_text = f"{prop}*:" if is_mandatory else f"{prop}:"
            ttk.Label(form_frame, text=label_text).grid(row=row_counter, column=0, sticky="w", pady=2)
            
            entry = ttk.Entry(form_frame, width=40)
            entry.grid(row=row_counter, column=1, sticky="ew", pady=2)
            if initial_data and prop in initial_data:
                entry.insert(0, initial_data[prop])
            self.entries[prop] = entry
            row_counter += 1

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=row_counter, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Submit", command=self.submit).pack(side="left", padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="left", padx=10)
        
        self.transient(parent)
        self.grab_set()

    def submit(self):
        self.result = {}
        for prop, entry in self.entries.items():
            value = entry.get()
            if prop == "genNumber":
                try:
                    self.result[prop] = int(value)
                except ValueError:
                    messagebox.showerror("Invalid Input", "Generation number must be an integer.")
                    return
            else:
                self.result[prop] = value
        
        # --- Auto-generate ID for children and siblings ---
        if self.relationship_type in ["child", "sibling"]:
            child_num = self.entries.get("childNumber").get()
            if not child_num:
                messagebox.showerror("ID Error", "'childNumber' is required to generate an ID.")
                return
            
            # For siblings, we need the parent's ID, not the sibling's ID
            id_base = self.related_person_id
            if self.relationship_type == 'sibling':
                # Fetch the parent ID
                parent_id_records = self.master.run_query(
                    "MATCH (:Person {id: $id})-[:CHILD_OF]->(p:Person) RETURN p.id as id LIMIT 1",
                    id=self.related_person_id
                )
                if not parent_id_records:
                    messagebox.showerror("ID Error", "Could not find a parent to generate the ID.")
                    return
                id_base = parent_id_records[0]['id']

            self.result['id'] = f"{id_base}_{child_num}"
        elif self.relationship_type == "spouse": # For spouses, prompt for ID
             self.result['id'] = simpledialog.askstring("Person ID", "Enter a unique ID for the new spouse:")
        # For modify, the ID is not needed in the result
        
        self.destroy()

# --- Main Execution Block ---
if __name__ == "__main__":
    app = FamilyTreeApp()
    app.mainloop()

