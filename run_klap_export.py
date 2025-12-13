#!/usr/bin/env python3
"""Export Klap clips and store with download URLs"""
import psycopg2, os, requests, time, sys
from datetime import datetime
from dotenv import load_dotenv

# Load env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

KLAP_API_KEY = os.getenv('KLAP_API_KEY')
API_URL = 'https://api.klap.app/v2'
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {KLAP_API_KEY}'
}

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

# Known data
folder_id = 'lj7NTsH6'
source_video_url = 'https://www.youtube.com/watch?v=fLoJqPv2niI'
parent_project_id = '9KSfXrWH5IrFoS2p'

print('🚀 KLAP SHORTS WORKFLOW - Full Database Storage')
print('=' * 70)
print()

# Step 1: Create parent record
print('📦 Step 1: Creating parent record...')
cursor.execute('''
    INSERT INTO video_to_shorts_agent (
        id, status, src_url, project_id, name, author_id, created_at,
        folder_id, descriptions
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status
''', (
    parent_project_id, 'processing', source_video_url, parent_project_id,
    '[PARENT] Klap Job', 2, datetime.now(), folder_id,
    'Parent job - processing clips'
))
conn.commit()
print(f'   ✅ Parent: {parent_project_id}')
print()

# Step 2: Fetch clips from Klap
print('📹 Step 2: Fetching clips from Klap API...')
response = requests.get(f'{API_URL}/projects/{folder_id}', headers=headers)
clips = response.json()
print(f'   Found {len(clips)} clips')
print()

# Step 3: Export each clip and store with download URL
print('📤 Step 3: Exporting clips and storing with download URLs...')
print('=' * 70)

successful = 0
for i, clip in enumerate(clips):
    clip_id = clip.get('id')
    clip_name = clip.get('name', f'Clip {i+1}')
    virality = clip.get('virality_score', 0)
    explanation = clip.get('virality_score_explanation', '')
    
    print(f'\n🎬 Clip {i+1}/{len(clips)}: {clip_name[:50]}...')
    print(f'   ID: {clip_id}')
    print(f'   Virality: {virality}')
    
    # Start export
    print(f'   📤 Starting export...')
    try:
        export_resp = requests.post(
            f'{API_URL}/projects/{folder_id}/{clip_id}/exports',
            headers=headers,
            json={}
        )
        export_data = export_resp.json()
        export_id = export_data.get('id')
        print(f'   Export ID: {export_id}')
        
        # Poll for completion
        output_url = None
        for attempt in range(30):  # Max ~7.5 min
            status_resp = requests.get(
                f'{API_URL}/projects/{folder_id}/{clip_id}/exports/{export_id}',
                headers=headers
            )
            status_data = status_resp.json()
            status = status_data.get('status')
            
            if status in ['success', 'complete', 'ready']:
                output_url = status_data.get('src_url')
                print(f'   ✅ Export complete! (status: {status})')
                print(f'   📹 Download URL: {output_url}')
                break
            elif status == 'error':
                print(f'   ❌ Export failed')
                break
            else:
                print(f'   ⏳ {status}... (attempt {attempt+1})')
                time.sleep(10)  # Poll every 10 seconds
        
        # Store in database
        if output_url:
            cursor.execute('''
                INSERT INTO video_to_shorts_agent (
                    id, status, src_url, output_video_url, project_id, name, 
                    author_id, created_at, finished_at, folder_id, 
                    virality_score, virality_score_explanation, descriptions
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    output_video_url = EXCLUDED.output_video_url,
                    status = EXCLUDED.status,
                    finished_at = EXCLUDED.finished_at
            ''', (
                clip_id, 'exported', source_video_url, output_url, parent_project_id,
                clip_name, 2, datetime.now(), datetime.now(), folder_id,
                virality, explanation, f'Individual clip from {parent_project_id}'
            ))
            conn.commit()
            print(f'   💾 Saved to database!')
            successful += 1
        else:
            # Store without URL
            cursor.execute('''
                INSERT INTO video_to_shorts_agent (
                    id, status, src_url, project_id, name, author_id, created_at,
                    folder_id, virality_score, descriptions
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            ''', (
                clip_id, 'export_failed', source_video_url, parent_project_id,
                clip_name, 2, datetime.now(), folder_id, virality,
                'Export failed - no download URL'
            ))
            conn.commit()
            
    except Exception as e:
        print(f'   ❌ Error: {e}')

# Update parent with final status
cursor.execute('''
    UPDATE video_to_shorts_agent 
    SET status = 'complete', 
        name = %s,
        descriptions = %s,
        finished_at = NOW()
    WHERE id = %s
''', (
    f'[PARENT] Klap Job - {len(clips)} clips',
    f'Completed: {successful}/{len(clips)} clips exported with download URLs',
    parent_project_id
))
conn.commit()

print()
print('=' * 70)
print(f'✅ COMPLETE! {successful}/{len(clips)} clips stored with download URLs')
print()

# Show final database state
cursor.execute('''
    SELECT id, name, status, virality_score, output_video_url 
    FROM video_to_shorts_agent 
    ORDER BY CASE WHEN name LIKE '[PARENT]%' THEN 0 ELSE 1 END, virality_score DESC NULLS LAST
''')
print('📊 FINAL DATABASE STATE:')
print('-' * 70)
for row in cursor.fetchall():
    is_parent = '[PARENT]' in (row[1] or '')
    if is_parent:
        print(f'🏠 {row[0]}: {row[1]} ({row[2]})')
    else:
        has_url = '✅' if row[4] else '❌'
        print(f'   {has_url} {row[0]}: Virality {row[3]} | {row[2]}')
        if row[4]:
            print(f'      URL: {row[4][:60]}...')

cursor.close()
conn.close()

