"""
Supabase Database Client
Handles all database operations for the parking monitoring system
"""

import os
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

class SupabaseClient:
    """Client for interacting with Supabase database"""

    def __init__(self):
        """Initialize Supabase client"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')

        if not self.url or not self.key:
            print("[WARNING] Supabase credentials not found. Using local storage only.")
            self.client: Optional[Client] = None
        else:
            try:
                self.client = create_client(self.url, self.key)
                print("[SUCCESS] Connected to Supabase successfully")
            except Exception as e:
                print(f"[ERROR] Failed to connect to Supabase: {e}")
                self.client = None

    def is_connected(self) -> bool:
        """Check if connected to Supabase"""
        return self.client is not None

    # CAMERA OPERATIONS

    def save_camera(self, camera_id: str, name: str, location: str, url: str,
                   status: str = 'offline', areas_count: int = 0) -> bool:
        """Save or update camera information"""
        if not self.is_connected():
            return False

        try:
            data = {
                'id': camera_id,
                'name': name,
                'location': location,
                'url': url,
                'status': status,
                'areas_count': areas_count,
                'updated_at': datetime.now().isoformat()
            }

            # Upsert (insert or update)
            self.client.table('cameras').upsert(data).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Error saving camera: {e}")
            return False

    def get_camera(self, camera_id: str) -> Optional[Dict]:
        """Get camera by ID"""
        if not self.is_connected():
            return None

        try:
            response = self.client.table('cameras').select('*').eq('id', camera_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"[ERROR] Error getting camera: {e}")
            return None

    def get_all_cameras(self) -> List[Dict]:
        """Get all cameras"""
        if not self.is_connected():
            return []

        try:
            response = self.client.table('cameras').select('*').execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"[ERROR] Error getting cameras: {e}")
            return []

    def update_camera_status(self, camera_id: str, status: str) -> bool:
        """Update camera status"""
        if not self.is_connected():
            return False

        try:
            self.client.table('cameras').update({
                'status': status,
                'updated_at': datetime.now().isoformat()
            }).eq('id', camera_id).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Error updating camera status: {e}")
            return False

    def update_camera_stream_url(self, camera_id: str, stream_url: str) -> bool:
        """Update camera stream URL"""
        if not self.is_connected():
            return False

        try:
            self.client.table('cameras').update({
                'stream_url': stream_url,
                'updated_at': datetime.now().isoformat()
            }).eq('id', camera_id).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Error updating camera stream URL: {e}")
            return False

    def delete_camera(self, camera_id: str) -> bool:
        """Delete camera (cascades to related records)"""
        if not self.is_connected():
            return False

        try:
            self.client.table('cameras').delete().eq('id', camera_id).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Error deleting camera: {e}")
            return False

    # PARKING AREA OPERATIONS

    def save_parking_areas(self, camera_id: str, areas: List[Dict]) -> bool:
        """Save parking areas for a camera"""
        if not self.is_connected():
            return False

        try:
            # Delete existing areas for this camera
            self.client.table('parking_areas').delete().eq('camera_id', camera_id).execute()

            # Insert new areas
            for idx, area in enumerate(areas):
                data = {
                    'camera_id': camera_id,
                    'area_index': idx,
                    'points': area['points']
                }
                self.client.table('parking_areas').insert(data).execute()

            # Update camera areas_count
            self.client.table('cameras').update({
                'areas_count': len(areas),
                'updated_at': datetime.now().isoformat()
            }).eq('id', camera_id).execute()

            return True
        except Exception as e:
            print(f"[ERROR] Error saving parking areas: {e}")
            return False

    def get_parking_areas(self, camera_id: str) -> List[Dict]:
        """Get parking areas for a camera"""
        if not self.is_connected():
            return []

        try:
            response = self.client.table('parking_areas').select('*').eq('camera_id', camera_id).order('area_index').execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"[ERROR] Error getting parking areas: {e}")
            return []

    # OCCUPANCY HISTORY OPERATIONS

    def save_occupancy(self, camera_id: str, total_spots: int, occupied_spots: int,
                      free_spots: int, occupancy_percentage: float, fps: float = None,
                      details: Dict = None) -> bool:
        """Save occupancy snapshot"""
        if not self.is_connected():
            return False

        try:
            data = {
                'camera_id': camera_id,
                'timestamp': datetime.now().isoformat(),
                'total_spots': total_spots,
                'occupied_spots': occupied_spots,
                'free_spots': free_spots,
                'occupancy_percentage': occupancy_percentage,
                'fps': fps,
                'details': details
            }
            self.client.table('occupancy_history').insert(data).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Error saving occupancy: {e}")
            return False

    def get_latest_occupancy(self, camera_id: str) -> Optional[Dict]:
        """Get latest occupancy for a camera"""
        if not self.is_connected():
            return None

        try:
            response = self.client.table('occupancy_history').select('*').eq('camera_id', camera_id).order('timestamp', desc=True).limit(1).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"[ERROR] Error getting latest occupancy: {e}")
            return None

    def get_occupancy_history(self, camera_id: str, hours: int = 24) -> List[Dict]:
        """Get occupancy history for the last N hours"""
        if not self.is_connected():
            return []

        try:
            response = self.client.table('occupancy_history').select('*').eq('camera_id', camera_id).gte('timestamp', f'now() - interval \'{hours} hours\'').order('timestamp', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"[ERROR] Error getting occupancy history: {e}")
            return []

    # EVENT OPERATIONS

    def log_event(self, camera_id: str, event_type: str, description: str = None,
                 metadata: Dict = None) -> bool:
        """Log system event"""
        if not self.is_connected():
            return False

        try:
            data = {
                'camera_id': camera_id,
                'event_type': event_type,
                'description': description,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata
            }
            self.client.table('events').insert(data).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Error logging event: {e}")
            return False

    def get_recent_events(self, camera_id: str = None, limit: int = 50) -> List[Dict]:
        """Get recent events"""
        if not self.is_connected():
            return []

        try:
            query = self.client.table('events').select('*')
            if camera_id:
                query = query.eq('camera_id', camera_id)
            response = query.order('timestamp', desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"[ERROR] Error getting events: {e}")
            return []

    # STATISTICS OPERATIONS

    def save_daily_statistics(self, camera_id: str, stats_date: date,
                             avg_occupancy: float, max_occupancy: float,
                             min_occupancy: float, total_entries: int,
                             peak_hour: int = None) -> bool:
        """Save or update daily statistics"""
        if not self.is_connected():
            return False

        try:
            data = {
                'camera_id': camera_id,
                'date': stats_date.isoformat(),
                'avg_occupancy': avg_occupancy,
                'max_occupancy': max_occupancy,
                'min_occupancy': min_occupancy,
                'total_entries': total_entries,
                'peak_hour': peak_hour
            }
            # Upsert based on camera_id and date
            self.client.table('daily_statistics').upsert(data).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Error saving daily statistics: {e}")
            return False

    def get_daily_statistics(self, camera_id: str, days: int = 7) -> List[Dict]:
        """Get daily statistics for the last N days"""
        if not self.is_connected():
            return []

        try:
            response = self.client.table('daily_statistics').select('*').eq('camera_id', camera_id).gte('date', f'now() - interval \'{days} days\'').order('date', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"[ERROR] Error getting daily statistics: {e}")
            return []

    # VIEWS

    def get_realtime_stats(self) -> List[Dict]:
        """Get real-time stats from view"""
        if not self.is_connected():
            return []

        try:
            response = self.client.table('camera_stats_realtime').select('*').execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"[ERROR] Error getting realtime stats: {e}")
            return []

# Global instance
db = SupabaseClient()
