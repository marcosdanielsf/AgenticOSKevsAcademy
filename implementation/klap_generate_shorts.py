import os
import time
import json
import requests
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv('KLAP_API_KEY')

if not API_KEY:
    # Try to look in parent directory .env if not found
    parent_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(parent_env):
        load_dotenv(parent_env)
        API_KEY = os.getenv('KLAP_API_KEY')

# Configuration
API_URL = "https://api.klap.app/v2"

if not API_KEY:
    raise ValueError("KLAP_API_KEY not found in .env file or environment variables")

def get_headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

def submit_video(video_url, language="en"):
    """Submit a video for processing"""
    endpoint = f"{API_URL}/tasks/video-to-shorts"
    payload = {
        "source_video_url": video_url,
        "language": language,
        "max_duration": 30,
        "max_clip_count": 5,
        "editing_options": {
            "intro_title": False
        }
    }
    
    print(f"Submitting video: {video_url}")
    response = requests.post(endpoint, headers=get_headers(), json=payload)
    response.raise_for_status()
    return response.json()

def poll_task(task_id):
    """Poll task status until complete"""
    endpoint = f"{API_URL}/tasks/{task_id}"
    
    while True:
        response = requests.get(endpoint, headers=get_headers())
        response.raise_for_status()
        data = response.json()
        status = data.get("status")
        
        print(f"Task Status: {status}")
        
        if status == "success" or status == "complete" or status == "ready":
            return data
        elif status == "error":
            raise Exception(f"Task failed: {data.get('error_message', 'Unknown error')}")
        
        time.sleep(30)

def list_shorts(folder_id):
    """List generated shorts from the folder"""
    endpoint = f"{API_URL}/projects/{folder_id}"
    
    print(f"Listing shorts for folder: {folder_id}")
    response = requests.get(endpoint, headers=get_headers())
    response.raise_for_status()
    return response.json()

def export_short(folder_id, project_id):
    """Export a specific short"""
    endpoint = f"{API_URL}/projects/{folder_id}/{project_id}/exports"
    # Default watermark settings or empty if not needed
    payload = {
        "watermark": {
             "src_url": "https://studio.restream.io/logos/default.png", # Example or make optional
             "pos_x": 0.5,
             "pos_y": 0.5,
             "scale": 1
        }
    }
    
    print(f"Exporting project: {project_id}")
    response = requests.post(endpoint, headers=get_headers(), json=payload)
    response.raise_for_status()
    return response.json()

def poll_export(folder_id, project_id, export_id):
    """Poll export status"""
    endpoint = f"{API_URL}/projects/{folder_id}/{project_id}/exports/{export_id}"
    
    while True:
        response = requests.get(endpoint, headers=get_headers())
        response.raise_for_status()
        data = response.json()
        status = data.get("status")
        
        print(f"Export Status: {status}")
        
        if status == "success" or status == "complete":
            return data
        elif status == "error":
            raise Exception("Export failed")
        
        time.sleep(15)

def main():
    parser = argparse.ArgumentParser(description="Generate shorts from video using Klap API")
    parser.add_argument("url", help="Source video URL (YouTube, S3, etc.)")
    args = parser.parse_args()

    try:
        # 1. Submit
        task = submit_video(args.url)
        task_id = task.get("id")
        print(f"Task started with ID: {task_id}")

        # 2. Poll Task
        completed_task = poll_task(task_id)
        folder_id = completed_task.get("output_id")
        print(f"Processing complete. Folder ID: {folder_id}")

        # 3. List Shorts
        shorts = list_shorts(folder_id)
        print(f"Found {len(shorts)} shorts.")
        
        for short in shorts:
            print(f"- {short.get('name')} (Virality: {short.get('virality_score')})")

        # 4. Export the best short (highest virality)
        if shorts:
            best_short = max(shorts, key=lambda x: x.get('virality_score', 0))
            print(f"Exporting best short: {best_short.get('name')}")
            
            export_task = export_short(folder_id, best_short.get('id'))
            export_id = export_task.get("id")
            
            final_export = poll_export(folder_id, best_short.get('id'), export_id)
            print(f"Export Complete! Video URL: {final_export.get('src_url')}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
