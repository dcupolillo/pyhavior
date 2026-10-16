""" 
Generic Protocol Runner - executes protocols from sequence files
Created on October 3, 2025
@author: dcupolillo 
"""
import sys
import json
import time
from pathlib import Path
from serial import Serial
from pyhavior.core.serial_messages import SerialMessages


class ProtocolRunner:
    """
    Generic protocol runner that executes sequences loaded from external files.
    
    This is a standalone executor that loads and runs protocol sequences
    defined in JSON files, without needing to inherit complex behavioral test logic.
    """

    def __init__(
            self,
            sequence_file: str = None
    ) -> None:
        """
        Initialize protocol runner with optional sequence file.
        
        Parameters
        ----------
        sequence_file: str, optional
            Path to JSON sequence file, or None to load later
        """

        self.sequence_file = sequence_file
        self.protocol_data = {}
        self.sequence = []
        self.duration = 300
        self.protocol_name = "Unknown Protocol"
        
        # Serial communication
        self.messages = SerialMessages()
        self.ser = None
        self.running = False
        self.stop_requested = False
        
        if sequence_file:
            self.load_sequence(sequence_file)

    def load_sequence(
            self,
            file_path: str
    ) -> None:
        """
        Load protocol sequence from JSON file.

        Parameters
        ----------
        file_path: str
            Path to JSON sequence file
            
        Raises
        ------
        FileNotFoundError: If sequence file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
        KeyError: If required fields are missing
        """
        sequence_path = Path(file_path)
        
        if not sequence_path.exists():
            # Try relative to protocols directory
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                # Running in PyInstaller bundle
                protocols_dir = Path(sys._MEIPASS) / "protocols"
            else:
                # Running in normal Python environment
                protocols_dir = Path(__file__).parent.parent / "protocols"
                
            sequence_path = protocols_dir / f"{file_path}.json"
            
            if not sequence_path.exists():
                raise FileNotFoundError(f"Sequence file not found: {file_path}")
        
        try:
            with open(sequence_path, 'r') as f:
                self.protocol_data = json.load(f)
            
            # Extract protocol information
            self.protocol_name = self.protocol_data.get('protocol_name', 'Unknown')
            self.duration = self.protocol_data.get('duration', 300)
            
            # Build sequence from JSON data
            self._build_sequence_from_data()
            
            print(f"Loaded protocol: {self.protocol_name}")
            print(f"Duration: {self.duration}s")
            print(f"Sequence events: {len(self.sequence)}")
            
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in sequence file: {e}")
        
        except Exception as e:
            raise Exception(f"Error loading sequence file: {e}")

    def _build_sequence_from_data(self) -> None:
        """
        Build the execution sequence from loaded JSON data.
        
        Converts JSON sequence events into the format expected by the runner:
        (time, message, duration, message_off, description)
        """
        self.sequence = []
        
        if 'sequence' not in self.protocol_data:
            raise KeyError("No 'sequence' field found in protocol data")
        
        for event in self.protocol_data['sequence']:
            try:
                event_time = float(event['time'])
                device = event['device'].lower()
                action = event['action'].upper()
                description = event.get('description', f"{device} {action}")
                
                # Map device names to serial messages
                message = self._get_device_message(device, action)
                
                if message:
                    # Add event as (time, message, 0, None, description)
                    self.sequence.append((event_time, message, 0, None, description))
                else:
                    print(f"Warning: Unknown device '{device}' with action '{action}'")
                    
            except (KeyError, ValueError, TypeError) as e:
                print(f"Warning: Skipping invalid sequence event: {event} - {e}")

    def _get_device_message(
            self,
            device: str,
            action: str
    ) -> bytes:
        """
        Get the appropriate serial message for a device action.
        
        Parameters
        ----------
        device: str
            Device name (tone, shock, pump, buzzer, white_noise)
        action: str
            Action (ON or OFF)

        Returns:
            Serial message bytes or None if unknown device/action
        """

        if device not in ['tone', 'shock', 'pump', 'buzzer', 'white_noise']:
            return None
        
        if action not in ['ON', 'OFF']:
            return None
        
        device_mapping = {
            'tone': {
                'ON': self.messages.tone_on,
                'OFF': self.messages.tone_off
            },
            'shock': {
                'ON': self.messages.shock_on,
                'OFF': self.messages.shock_off
            },
            'pump': {
                'ON': self.messages.pump_on,
                'OFF': self.messages.pump_off
            },
            'buzzer': {
                'ON': self.messages.buzzer_on,
                'OFF': self.messages.buzzer_off
            },
            'white_noise': {
                'ON': self.messages.white_noise_on,
                'OFF': self.messages.white_noise_off
            }
        }
        
        return device_mapping.get(device, {}).get(action)

    def run(self, ser: Serial) -> None:
        """
        Execute the loaded protocol sequence.
        
        Args:
            ser: Serial connection to Arduino
        """
        if not self.sequence:
            print("No sequence loaded. Cannot run protocol.")
            return
            
        self.ser = ser
        start_time = time.time()
        
        # Track which sequence events have been fired
        fired = [False] * len(self.sequence)
        
        print(f"Starting protocol: {self.protocol_name}")
        print(f"Total duration: {self.duration}s")

        while (time.time() - start_time < self.duration and
               not self.stop_requested):

            now = time.time() - start_time

            for i, (event_time, message, _, __, description) in enumerate(self.sequence):
                if not fired[i] and now >= event_time:
                    # Fire the action once
                    try:
                        if self.ser and message:
                            self.ser.write(message)
                            print(
                                f"{description} - "
                                f"[{time.strftime('%H:%M:%S', time.localtime())}]")
                                        
                    except Exception as e:
                        # Keep running even if serial write fails
                        print(f"ProtocolRunner serial error: {e}")
                    finally:
                        fired[i] = True

            time.sleep(0.01)  # Small delay to reduce CPU usage

        print(f"Protocol completed: {self.protocol_name}")
        self.running = False
        
        if self.ser and getattr(self.ser, 'is_open', False):
            try:
                self.ser.close()
            except Exception:
                pass

    def stop(self) -> None:
        """Stop the protocol execution"""
        self.running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass

    def request_stop(self) -> None:
        """Request protocol to stop at next opportunity"""
        self.stop_requested = True

    def get_protocol_info(self) -> dict:
        """
        Get information about the loaded protocol.
        
        Returns:
            Dictionary containing protocol metadata
        """
        return {
            'name': self.protocol_name,
            'duration': self.duration,
            'sequence_length': len(self.sequence),
            'description': self.protocol_data.get('description', ''),
            'parameters': self.protocol_data.get('parameters', {}),
            'file_path': self.sequence_file
        }

    @staticmethod
    def list_available_protocols(
        sequences_dir: str = None
    ) -> list:
        """
        List all available protocol sequence files.
        
        Args:
            sequences_dir: Directory to search for sequence files
            
        Returns:
            List of protocol names (without .json extension)
        """
        if sequences_dir is None:
            sequences_dir = Path(__file__).parent.parent.parent / "protocols"
        else:
            sequences_dir = Path(sequences_dir)
        
        if not sequences_dir.exists():
            return []
        
        protocols = []
        for json_file in sequences_dir.glob("*.json"):
            protocols.append(json_file.stem)  # Filename without extension
            
        return sorted(protocols)


# Auto-discover available protocols from JSON files
def _get_available_protocols():
    """Dynamically discover available protocol sequence files"""
    try:
        
        # Handle PyInstaller bundled app
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running in PyInstaller bundle
            protocols_dir = Path(sys._MEIPASS) / "protocols"
        else:
            # Running in normal Python environment
            protocols_dir = Path(__file__).parent.parent / "protocols"
        
        if not protocols_dir.exists():
            print(f"Protocols directory not found: {protocols_dir}")  # Debug
            return []
        
        # Find all .json files and return their names without extension
        protocols = []
        for json_file in protocols_dir.glob("*.json"):
            protocols.append(json_file.stem)  # filename without .json extension

        return sorted(protocols)
        
    except Exception as e:
        print(f"Error discovering protocols: {e}")  # Debug
        # Fallback to hardcoded list if discovery fails
        return [
            "fear_conditioning",
            "fear_recall", 
            "habituation"
        ]

AVAILABLE_PROTOCOLS = _get_available_protocols()