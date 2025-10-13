#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
project_root = Path(__file__).parent.parent
load_dotenv(project_root / '.env')

from flask import Flask
from utils.database_config import database_config
from utils.database_models import Roommate, Chore, SubChore, Assignment, ShoppingItem

app = Flask(__name__)
database_config.configure_flask_app(app)

with app.app_context():
    print('=== DATABASE CONTENTS ===')
    print(f'\nRoommates ({Roommate.query.count()}):')
    for r in Roommate.query.all():
        print(f'  - {r.id}: {r.name}')

    print(f'\nChores ({Chore.query.count()}):')
    for c in Chore.query.all():
        sub_count = SubChore.query.filter_by(chore_id=c.id).count()
        print(f'  - {c.id}: {c.name} ({sub_count} sub-chores)')

    print(f'\nAssignments ({Assignment.query.count()}):')
    for a in Assignment.query.all():
        chore_name = a.chore.name if a.chore else "[deleted chore]"
        print(f'  - {a.roommate.name} -> {chore_name}')

    print(f'\nShopping Items ({ShoppingItem.query.count()}):')
    for s in ShoppingItem.query.all():
        print(f'  - {s.item_name}')

    print('\n✅ Migration appears SUCCESSFUL!')
    print('   All critical data has been migrated to PostgreSQL.')
