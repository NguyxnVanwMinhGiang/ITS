"""
Traffic Density Service
Calculates traffic density based on hourly historical comparison.
"""
from datetime import datetime
from typing import Optional
from app.models.detection import Detection, ZonePolygon
from app.services.hourly_density_storage import HourlyDensityStorage


VEHICLE_ONLY_CLASSES = {"car", "motorcycle", "bus", "truck", "bicycle"}

# Thresholds based on absolute flow rate (xe/giờ)
# <3500 = light, 3500-6500 = medium, >6500 = heavy
DENSITY_THRESHOLDS = {
    "overload": 4500,
    "heavy": 3000,
    "medium": 1500,
}

DENSITY_LABELS = {
    "overload": "Quá tải",
    "heavy": "Cao",
    "medium": "Trung bình",
    "light": "Ít",
}


def _point_in_polygon(x: float, y: float, polygon_points: list) -> bool:
    """Check if point is inside polygon using ray casting algorithm."""
    n = len(polygon_points)
    if n < 3:
        return False

    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon_points[i].x, polygon_points[i].y
        xj, yj = polygon_points[j].x, polygon_points[j].y
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _is_detection_in_ignore_zone(det: Detection, zones: list[ZonePolygon]) -> bool:
    """Check if detection's center is in any ignore zone."""
    cx = (det.bbox.x1 + det.bbox.x2) / 2
    cy = (det.bbox.y1 + det.bbox.y2) / 2

    for zone in zones:
        if zone.is_ignore_zone and _point_in_polygon(cx, cy, zone.points):
            return True
    return False


def filter_detections_by_ignore_zones(detections: list[Detection], zones: list[ZonePolygon]) -> list[Detection]:
    """Filter out detections that are in ignore zones. Used globally for detection display."""
    if not zones:
        return detections
    
    ignore_zones = [z for z in zones if z.is_ignore_zone]
    if not ignore_zones:
        return detections
    
    return [det for det in detections if not _is_detection_in_ignore_zone(det, ignore_zones)]


class TrafficDensityTracker:
    """Tracks vehicle detections for density calculation."""

    def __init__(self, camera_id: str, duration_minutes: int):
        self.camera_id = camera_id
        self.duration_minutes = duration_minutes
        self.start_time = datetime.now()
        self.start_hour = self.start_time.hour
        self.tracked_vehicle_ids: set[int] = set()
        self.vehicle_breakdown: dict[str, set[int]] = {
            cls: set() for cls in VEHICLE_ONLY_CLASSES
        }
        self.is_tracking = True

    def track_vehicles(self, detections: list[Detection], zones: list[ZonePolygon] = None) -> int:
        """Track unique vehicles from detections. Returns current count."""
        if not self.is_tracking:
            return len(self.tracked_vehicle_ids)

        zones = zones or []

        for det in detections:
            if det.class_name not in VEHICLE_ONLY_CLASSES:
                continue
            if det.track_id is None:
                continue
            # Skip vehicles in ignore zones
            if zones and _is_detection_in_ignore_zone(det, zones):
                continue

            self.tracked_vehicle_ids.add(det.track_id)
            self.vehicle_breakdown[det.class_name].add(det.track_id)

        return len(self.tracked_vehicle_ids)

    def get_current_count(self) -> int:
        """Get current unique vehicle count."""
        return len(self.tracked_vehicle_ids)

    def get_elapsed_minutes(self) -> float:
        """Get elapsed time in minutes."""
        elapsed = datetime.now() - self.start_time
        return elapsed.total_seconds() / 60

    def calculate_density(self) -> dict:
        """Calculate density using q = n/t formula (vehicles per hour)."""
        self.is_tracking = False
        end_time = datetime.now()

        total_vehicles = len(self.tracked_vehicle_ids)
        elapsed_hours = self.get_elapsed_minutes() / 60
        
        # q = n/t (vehicles per hour)
        if elapsed_hours > 0:
            flow_rate = total_vehicles / elapsed_hours
        else:
            flow_rate = 0
        
        # Get hourly average flow rate for the same hour
        hourly_avg_count = HourlyDensityStorage.get_hourly_average(
            self.camera_id, self.start_hour
        )
        
        # Convert hourly average count to flow rate (assuming same duration)
        if elapsed_hours > 0:
            hourly_avg_flow = hourly_avg_count / elapsed_hours if hourly_avg_count > 0 else 0
        else:
            hourly_avg_flow = hourly_avg_count
        
        # Save current count to history
        HourlyDensityStorage.save_hourly_count(
            self.camera_id, self.start_hour, total_vehicles
        )
        
        # Calculate percentage compared to historical average
        if hourly_avg_flow > 0:
            percentage = (flow_rate / hourly_avg_flow) * 100
        else:
            # First time - use 50% as baseline (middle range)
            percentage = 50.0
        
        # Determine density level based on absolute flow rate thresholds
        # >4500 = overload (Quá tải), 3000-4500 = heavy (Cao),
        # 1500-3000 = medium (Trung bình), <1500 = light (Ít)
        if flow_rate >= DENSITY_THRESHOLDS["overload"]:
            density_level = "overload"
        elif flow_rate >= DENSITY_THRESHOLDS["heavy"]:
            density_level = "heavy"
        elif flow_rate >= DENSITY_THRESHOLDS["medium"]:
            density_level = "medium"
        else:
            density_level = "light"

        breakdown = {cls: len(ids) for cls, ids in self.vehicle_breakdown.items()}
        breakdown = {k: v for k, v in breakdown.items() if v > 0}

        return {
            "camera_id": self.camera_id,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_minutes": self.duration_minutes,
            "hour": self.start_hour,
            "total_vehicles": total_vehicles,
            "flow_rate": round(flow_rate, 2),
            "hourly_average": round(hourly_avg_flow, 2),
            "density_percentage": round(percentage, 2),
            "density_level": density_level,
            "density_label": DENSITY_LABELS[density_level],
            "vehicle_breakdown": breakdown,
        }

    def get_status(self) -> dict:
        """Get current tracking status."""
        return {
            "is_tracking": self.is_tracking,
            "current_count": len(self.tracked_vehicle_ids),
            "elapsed_minutes": round(self.get_elapsed_minutes(), 2),
            "duration_minutes": self.duration_minutes,
            "hour": self.start_hour,
        }


class TrafficDensityManager:
    """Manages traffic density trackers for multiple cameras."""

    _instances: dict[str, TrafficDensityTracker] = {}

    @classmethod
    def start_tracking(
        cls, camera_id: str, duration_minutes: int
    ) -> TrafficDensityTracker:
        """Start tracking for a camera."""
        tracker = TrafficDensityTracker(camera_id, duration_minutes)
        cls._instances[camera_id] = tracker
        return tracker

    @classmethod
    def get_tracker(cls, camera_id: str) -> Optional[TrafficDensityTracker]:
        """Get tracker for a camera."""
        return cls._instances.get(camera_id)

    @classmethod
    def stop_tracking(cls, camera_id: str) -> Optional[dict]:
        """Stop tracking and return result."""
        tracker = cls._instances.get(camera_id)
        if tracker:
            result = tracker.calculate_density()
            del cls._instances[camera_id]
            return result
        return None

    @classmethod
    def is_tracking(cls, camera_id: str) -> bool:
        """Check if camera is being tracked."""
        tracker = cls._instances.get(camera_id)
        return tracker is not None and tracker.is_tracking

    @classmethod
    def track_vehicles(cls, camera_id: str, detections: list[Detection], zones: list[ZonePolygon] = None) -> int:
        """Track vehicles for a camera. Returns current count."""
        tracker = cls._instances.get(camera_id)
        if tracker and tracker.is_tracking:
            return tracker.track_vehicles(detections, zones)
        return 0

    @classmethod
    def get_status(cls, camera_id: str) -> dict:
        """Get tracking status for a camera."""
        tracker = cls._instances.get(camera_id)
        if tracker:
            return tracker.get_status()
        return {"is_tracking": False, "current_count": 0}

    @classmethod
    def reset(cls, camera_id: str):
        """Reset tracker for a camera."""
        if camera_id in cls._instances:
            del cls._instances[camera_id]
