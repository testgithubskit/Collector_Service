# Collector_Service

Monorepo of Toyota/PLM collector services. Each folder is one collector (formerly a separate Git branch).

## Layout

| Folder | Description |
|--------|-------------|
| balluf_vibration_data | Balluff vibration data collector |
| cycletime_sql_server_data | Cycle time SQL Server -> Timescale |
| Disconnect_mechanism_GD | Disconnect mechanism (GD) |
| PARAM_comparison_TNGA_GD | PARAM comparison TNGA GD |
| PART_COUNT_TNGA | Part count TNGA |
| pressur_monitoring_disconnect_mechanism_TNGA | Pressure monitoring / disconnect TNGA |
| SPM_MCHINES_4 | SPM machines |
| STATIC_COLLECTOR_GD | Static collector GD (placeholder; source was a submodule) |
| tiei-reporter | TIEI reporter |
| TNGA_Static_and_Dynamic_collector | TNGA static + dynamic collector |

## Usage

Single branch (main). Work inside the folder for the service you need.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r <service_folder>\requirements.txt
```

Run the service from its folder (see that folder's main.py / docs).
