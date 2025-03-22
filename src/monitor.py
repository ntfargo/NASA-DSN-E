import requests
import sqlite3
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import xml.etree.ElementTree as ET
import io

class DSNMonitor:
    def __init__(self, data_config, db_config):
        """Initialize the monitor with data and database configurations."""
        self.dsnnow_url = data_config["dsnnow_url"]
        self.backup_source = data_config["backup_source"]
        self.db_file = db_config["file"]
        self.db_table = db_config["table"]

    def _connect_db(self):
        """Establish a connection to the SQLite database."""
        return sqlite3.connect(self.db_file)

    def _format_range(self, range_meters):
        """Format spacecraft range into a human-readable string."""
        if range_meters is None or range_meters <= 0:
            return "Unknown"
        
        # Convert to kilometers
        range_km = range_meters / 1000.0
        
        # Format based on distance
        if range_km >= 1000000:  # More than 1 million km
            return f"{range_km/1000000:.2f} million km"
        elif range_km >= 1000:  # More than 1000 km
            return f"{range_km/1000:.2f} thousand km"
        else:
            return f"{range_km:.2f} km"

    def _get_current_timestamp(self):
        return datetime.now()

    def _parse_xml_data(self, xml_content):
        """Parse DSNNow XML data into a list of records."""
        records = []
        current_timestamp = self._get_current_timestamp()
        
        try:
            # Parse XML content
            root = ET.fromstring(xml_content)
            
            # Find all dish elements
            for dish in root.findall('.//dish'):
                antenna_data = dish.attrib
                antenna_id = antenna_data.get('name', 'Unknown')
                
                # Get antenna angles
                azimuth = float(antenna_data.get('azimuthAngle', 0)) if antenna_data.get('azimuthAngle') not in ['', 'null', 'none'] else None
                elevation = float(antenna_data.get('elevationAngle', 0)) if antenna_data.get('elevationAngle') not in ['', 'null', 'none'] else None
                
                # Get target information
                target = dish.find('.//target')
                if target is not None:
                    spacecraft = target.get('name', 'Unknown')
                    # Get both upleg and downleg ranges
                    upleg_range = float(target.get('uplegRange', 0)) if target.get('uplegRange') not in ['', 'null', 'none'] else None
                    downleg_range = float(target.get('downlegRange', 0)) if target.get('downlegRange') not in ['', 'null', 'none'] else None
                    # Use the non-zero range, or average if both are available
                    spacecraft_range = None
                    if upleg_range and upleg_range > 0:
                        spacecraft_range = upleg_range
                    if downleg_range and downleg_range > 0:
                        if spacecraft_range:
                            spacecraft_range = (spacecraft_range + downleg_range) / 2
                        else:
                            spacecraft_range = downleg_range
                else:
                    spacecraft = 'Unknown'
                    spacecraft_range = None
                
                # Get all active downSignals
                down_signals = dish.findall('.//downSignal[@active="true"]')
                for signal in down_signals:
                    if signal.get('signalType') == 'data':
                        data_rate = float(signal.get('dataRate', 0)) if signal.get('dataRate') not in ['', 'null', 'none'] else None
                        frequency = float(signal.get('frequency', 0)) if signal.get('frequency') not in ['', 'null', 'none'] else None
                        power = float(signal.get('power', 0)) if signal.get('power') not in ['', 'null', 'none'] else None
                        
                        # Format the range for display
                        range_display = self._format_range(spacecraft_range)
                        
                        records.append({
                            "timestamp": current_timestamp.isoformat(),
                            "spacecraft": spacecraft,
                            "antenna_id": antenna_id,
                            "signal_strength": power if power is not None else 0.0,
                            "communication_duration": 0,  # Placeholder; predict this later
                            "data_rate": data_rate,
                            "frequency": frequency,
                            "azimuth": azimuth,
                            "elevation": elevation,
                            "spacecraft_range": spacecraft_range,
                            "range_display": range_display
                        })
                
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
        except Exception as e:
            print(f"Error processing XML data: {e}")
            
        return records

    def fetch_dsn_data(self):
        """Fetch real-time DSN data from DSNNow or fallback source."""
        try:
            # Add timestamp parameter to URL to prevent caching
            current_timestamp = self._get_current_timestamp()
            timestamp_param = str(round(float(current_timestamp.strftime("%s"))/5.0))
            url = f"{self.dsnnow_url}?r={timestamp_param}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Check if the response is XML
            content_type = response.headers.get('content-type', '').lower()
            if 'xml' in content_type or response.text.strip().startswith('<?xml'):
                return self._parse_xml_data(response.text)
            else:
                # Try parsing as JSON (backward compatibility)
                try:
                    data = response.json()
                    return self._parse_dsn_data(data)
                except ValueError:
                    raise ValueError("Response is neither XML nor JSON")
                    
        except (requests.RequestException, ValueError) as e:
            print(f"Failed to fetch from DSNNow: {e}. Trying backup source.")
            return self._fetch_backup_data()

    def _parse_dsn_data(self, data):
        """Parse DSNNow JSON data into a list of records."""
        records = []
        timestamp = datetime.utcnow().isoformat()
        for antenna in data.get("antennas", []):
            try:
                signal_strength = float(antenna.get("signal_strength", 0.0))
                records.append({
                    "timestamp": timestamp,
                    "spacecraft": antenna.get("spacecraft", "Unknown"),
                    "antenna_id": antenna.get("id", "Unknown"),
                    "signal_strength": signal_strength,
                    "communication_duration": 0,  # Placeholder; predict this later
                    "data_rate": None,
                    "frequency": None,
                    "azimuth": None,
                    "elevation": None,
                    "spacecraft_range": None,
                    "range_display": "Unknown"
                })
            except (ValueError, TypeError):
                continue  # Skip invalid records
        return records

    def _fetch_backup_data(self):
        """Fallback: Scrape Canberra DSN schedule if DSNNow fails."""
        try:
            response = requests.get(self.backup_source, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            records = []
            timestamp = datetime.utcnow().isoformat()
            
            for row in soup.select("table tr")[1:]:  # Skip header
                cols = row.find_all("td")
                if len(cols) >= 3:
                    try:
                        # Clean and parse the signal strength
                        signal_text = cols[2].text.strip()
                        # Remove any non-numeric characters except decimal point
                        signal_text = re.sub(r'[^\d.]', '', signal_text)
                        signal_strength = float(signal_text) if signal_text else 0.0
                        
                        records.append({
                            "timestamp": timestamp,
                            "spacecraft": cols[0].text.strip(),
                            "antenna_id": cols[1].text.strip(),
                            "signal_strength": signal_strength,
                            "communication_duration": 0,
                            "data_rate": None,
                            "frequency": None,
                            "azimuth": None,
                            "elevation": None,
                            "spacecraft_range": None,
                            "range_display": "Unknown"
                        })
                    except (ValueError, IndexError):
                        continue  # Skip invalid records
            return records
        except Exception as e:
            print(f"Backup fetch failed: {e}")
            return []

    def store_data(self, records):
        """Store fetched data in the SQLite database."""
        if not records:
            print("No valid records to store.")
            return
            
        conn = self._connect_db()
        cursor = conn.cursor()
        
        # Update table schema if needed
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.db_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                spacecraft TEXT,
                antenna_id TEXT,
                signal_strength REAL,
                communication_duration REAL,
                data_rate REAL,
                frequency REAL,
                azimuth REAL,
                elevation REAL,
                spacecraft_range REAL,
                range_display TEXT
            )
        """)
        
        query = f"""
            INSERT INTO {self.db_table} (
                timestamp, spacecraft, antenna_id, signal_strength, 
                communication_duration, data_rate, frequency, 
                azimuth, elevation, spacecraft_range, range_display
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            for record in records:
                cursor.execute(query, (
                    record["timestamp"],
                    record["spacecraft"],
                    record["antenna_id"],
                    record["signal_strength"],
                    record["communication_duration"],
                    record["data_rate"],
                    record["frequency"],
                    record["azimuth"],
                    record["elevation"],
                    record["spacecraft_range"],
                    record["range_display"]
                ))
            conn.commit()
            print(f"Stored {len(records)} records in database.")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()