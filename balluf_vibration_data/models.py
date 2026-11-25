from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MachineConfig:
    """Data model for machine configuration"""
    machine_id: int
    machine_name: str
    machine_location: str
    port1: str
    port2: str

    def to_postgres_tuple(self) -> tuple:
        """Convert to tuple for PostgreSQL insertion"""
        return (
            self.machine_id,
            self.machine_name,
            self.machine_location,
            self.port1,
            self.port2
        )


@dataclass
class VibrationDataPoint:
    """Data model for a single vibration data point from InfluxDB"""
    machine_id: int
    port: str
    timestamp: str
    origin: Optional[str]
    program_file_id: Optional[int] = None
    contact_temperature: Optional[float] = None
    v_peak_x: Optional[float] = None
    v_peak_y: Optional[float] = None
    v_peak_z: Optional[float] = None
    v_rms_x: Optional[float] = None
    v_rms_y: Optional[float] = None
    v_rms_z: Optional[float] = None

    @classmethod
    def from_influx_point(cls, machine_id: int, port: str, point: dict, program_file_id: Optional[int] = None) -> 'VibrationDataPoint':
        """Create a VibrationDataPoint from an InfluxDB query result point"""
        return cls(
            machine_id=machine_id,
            port=port,
            timestamp=point.get("time"),
            origin=point.get("origin"),
            program_file_id=program_file_id,
            contact_temperature=point.get("PD Contact Temp. [°C]"),
            v_peak_x=point.get("PD v-Peak X [mm/s]"),
            v_peak_y=point.get("PD v-Peak Y [mm/s]"),
            v_peak_z=point.get("PD v-Peak Z [mm/s]"),
            v_rms_x=point.get("PD v-RMS X [mm/s]"),
            v_rms_y=point.get("PD v-RMS Y [mm/s]"),
            v_rms_z=point.get("PD v-RMS Z [mm/s]")
        )

    def to_postgres_tuple(self) -> tuple:
        """Convert to tuple for PostgreSQL insertion"""
        return (
            self.timestamp,
            self.machine_id,
            self.program_file_id,
            self.port,
            self.origin,
            self.contact_temperature,
            self.v_peak_x,
            self.v_peak_y,
            self.v_peak_z,
            self.v_rms_x,
            self.v_rms_y,
            self.v_rms_z
        )


@dataclass
class VibrationMachineLog:
    """Data model for a cycle vibration log in vibration_machine_logs"""
    machine_id: int
    program_file_time: datetime
    port: Optional[str] = None
    contact_temperature: Optional[float] = None
    v_peak_x: Optional[float] = None
    v_peak_y: Optional[float] = None
    v_peak_z: Optional[float] = None
    v_rms_x: Optional[float] = None
    v_rms_y: Optional[float] = None
    v_rms_z: Optional[float] = None
    id: Optional[int] = None
    cycle_time: Optional[float] = None

    def to_postgres_tuple(self) -> tuple:
        """Convert to tuple for PostgreSQL insertion"""
        return (
            self.machine_id,
            self.program_file_time,
            self.port,
            self.contact_temperature,
            self.v_peak_x,
            self.v_peak_y,
            self.v_peak_z,
            self.v_rms_x,
            self.v_rms_y,
            self.v_rms_z,
            self.cycle_time
        )

