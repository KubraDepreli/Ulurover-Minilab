 #!/usr/bin/env python3
"""
Minilab Dashboard - Simple web interface for MQ-135 sensor data collection
with integrated camera support for Camera NoIR V2
"""
import os
import subprocess
import glob
import csv
import serial
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, send_file

app = Flask(__name__)

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_SCRIPT = os.path.join(BASE_DIR, 'read-dual-mq135-csv.py')
ARDUINO_A_SKETCH = os.path.join(BASE_DIR, 'arduino_a_master')
DATA_DIR = BASE_DIR
MEDIA_DIR = os.path.join(BASE_DIR, 'media')
PHOTOS_DIR = os.path.join(MEDIA_DIR, 'photos')
VIDEOS_DIR = os.path.join(MEDIA_DIR, 'videos')

# Create media directories if they don't exist
os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# Live monitoring state
live_monitor_active = False
live_serial_connection = None

# Camera streaming state
camera_stream_process = None
camera_recording_process = None

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    # Check for Arduino port
    ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    port_status = ports[0] if ports else None
    
    # Get list of recent CSV files
    csv_files = sorted(glob.glob(os.path.join(DATA_DIR, 'dual_co2_log_*.csv')), 
                      key=os.path.getmtime, reverse=True)[:5]
    csv_list = [os.path.basename(f) for f in csv_files]
    
    return jsonify({
        'arduino_port': port_status,
        'recent_files': csv_list,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/run', methods=['POST'])
def run_collection():
    """Run data collection with specified parameters"""
    try:
        data = request.get_json()
        duration = int(data.get('duration', 10))
        sensors_a = int(data.get('sensors_a', 1))
        sensors_b = int(data.get('sensors_b', 1))
        
        # Auto-detect port
        ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        if not ports:
            return jsonify({'success': False, 'error': 'No Arduino port found'}), 400
        
        port = ports[0]
        
        # Generate output filename
        output_file = os.path.join(DATA_DIR, f"dual_co2_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        # First, compile and upload Arduino sketch
        print(f"Compiling sketch for Arduino A ({sensors_a} sensor(s)) + Arduino B ({sensors_b} sensor(s))...")
        compile_cmd = ['arduino-cli', 'compile', '--fqbn', 'arduino:avr:uno', ARDUINO_A_SKETCH]
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({
                'success': False, 
                'error': 'Arduino compilation failed',
                'details': result.stderr
            }), 500
        
        print(f"Uploading sketch to {port}...")
        upload_cmd = ['arduino-cli', 'upload', '-p', port, '--fqbn', 'arduino:avr:uno', ARDUINO_A_SKETCH]
        result = subprocess.run(upload_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({
                'success': False, 
                'error': 'Arduino upload failed',
                'details': result.stderr
            }), 500
        
        # Wait for Arduino to reboot
        import time
        time.sleep(3)
        
        # Run data collection
        print(f"Starting data collection for {duration} seconds ({sensors_a} on A, {sensors_b} on B)...")
        cmd = [
            'python', PYTHON_SCRIPT,
            '--port', port,
            '--seconds', str(duration),
            '--output', output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 10)
        
        if result.returncode != 0:
            return jsonify({
                'success': False, 
                'error': 'Data collection failed',
                'details': result.stderr
            }), 500
        
        return jsonify({
            'success': True,
            'output_file': os.path.basename(output_file),
            'message': f'Data collected for {duration}s ({sensors_a} sensor(s) on Arduino A, {sensors_b} on Arduino B)',
            'log': result.stdout
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Data collection timeout'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data/<filename>', methods=['GET'])
def get_data(filename):
    """Get CSV data for plotting"""
    try:
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        data = {
            'timestamps': [],
            'sensors': {}
        }
        
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            
            # Initialize sensor data arrays
            for header in headers:
                if header != 'Seconds':
                    data['sensors'][header] = []
            
            # Read all rows
            for row in reader:
                data['timestamps'].append(float(row['Seconds']))
                for header in headers:
                    if header != 'Seconds':
                        try:
                            data['sensors'][header].append(float(row[header]))
                        except (ValueError, KeyError):
                            data['sensors'][header].append(None)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'data': data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live/start', methods=['POST'])
def start_live_monitor():
    """Start live monitoring"""
    global live_monitor_active, live_serial_connection
    
    try:
        if live_monitor_active:
            return jsonify({'success': False, 'error': 'Live monitor already running'}), 400
        
        # Find Arduino port
        ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        if not ports:
            return jsonify({'success': False, 'error': 'No Arduino port found'}), 400
        
        port = ports[0]
        
        # First, upload the Arduino sketch
        compile_cmd = ['arduino-cli', 'compile', '--fqbn', 'arduino:avr:uno', ARDUINO_A_SKETCH]
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({'success': False, 'error': 'Compilation failed'}), 500
        
        upload_cmd = ['arduino-cli', 'upload', '-p', port, '--fqbn', 'arduino:avr:uno', ARDUINO_A_SKETCH]
        result = subprocess.run(upload_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({'success': False, 'error': 'Upload failed'}), 500
        
        # Wait for Arduino to reboot
        time.sleep(3)
        
        # Open serial connection
        live_serial_connection = serial.Serial(port, 9600, timeout=2)
        live_monitor_active = True
        
        # Flush any initial garbage data
        time.sleep(0.5)
        live_serial_connection.reset_input_buffer()
        
        return jsonify({'success': True, 'message': 'Live monitoring started', 'port': port})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live/stop', methods=['POST'])
def stop_live_monitor():
    """Stop live monitoring"""
    global live_monitor_active, live_serial_connection
    
    try:
        if live_serial_connection:
            live_serial_connection.close()
            live_serial_connection = None
        
        live_monitor_active = False
        
        return jsonify({'success': True, 'message': 'Live monitoring stopped'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live/data', methods=['GET'])
def get_live_data():
    """Get current live sensor readings"""
    global live_monitor_active, live_serial_connection
    
    if not live_monitor_active or not live_serial_connection:
        return jsonify({'success': False, 'error': 'Live monitor not running'}), 400
    
    try:
        # Read a line from serial
        if live_serial_connection.in_waiting > 0:
            line = live_serial_connection.readline().decode('utf-8', errors='ignore').strip()
            
            if line and ',' in line and not line.lower().startswith('seconds'):
                parts = line.split(',')
                
                if len(parts) >= 2:
                    return jsonify({
                        'success': True,
                        'timestamp': float(parts[0]),
                        'sensors': {
                            f'CO2_PPM_B{i+1}': float(parts[i+1]) 
                            for i in range(len(parts) - 1)
                        }
                    })
        
        return jsonify({'success': True, 'data': None})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== CAMERA ENDPOINTS =====

@app.route('/api/camera/photo', methods=['POST'])
def capture_photo():
    """Capture a still photo using rpicam-still"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'photo_{timestamp}.jpg'
        filepath = os.path.join(PHOTOS_DIR, filename)
        
        # Use rpicam-still for photo capture (newer command)
        # -n or --nopreview: no preview window
        # -o: output file
        # -t: timeout in milliseconds (0 = immediate)
        cmd = [
            'rpicam-still',
            '-n',  # nopreview
            '-o', filepath,
            '-t', '0',  # Immediate capture
            '--width', '1920',
            '--height', '1080'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': 'Photo capture failed',
                'details': result.stderr
            }), 500
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'Photo file was not created'
            }), 500
        
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': f'/api/camera/media/photos/{filename}',
            'message': 'Photo captured successfully'
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Camera timeout'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/camera/video/start', methods=['POST'])
def start_video_recording():
    """Start video recording using rpicam-vid"""
    global camera_recording_process
    
    try:
        if camera_recording_process and camera_recording_process.poll() is None:
            return jsonify({'success': False, 'error': 'Recording already in progress'}), 400
        
        data = request.get_json()
        duration = int(data.get('duration', 10))  # Duration in seconds
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'video_{timestamp}.h264'
        filepath = os.path.join(VIDEOS_DIR, filename)
        
        # Use rpicam-vid for video recording
        # -n: nopreview
        # -t: duration in milliseconds
        # -o: output file
        cmd = [
            'rpicam-vid',
            '-n',  # nopreview
            '-o', filepath,
            '-t', str(duration * 1000),  # Convert to milliseconds
            '--width', '1920',
            '--height', '1080',
            '--framerate', '30'
        ]
        
        camera_recording_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        return jsonify({
            'success': True,
            'filename': filename,
            'duration': duration,
            'message': f'Video recording started for {duration} seconds'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/camera/video/status', methods=['GET'])
def video_recording_status():
    """Check if video recording is in progress"""
    global camera_recording_process
    
    if camera_recording_process and camera_recording_process.poll() is None:
        return jsonify({'recording': True})
    else:
        return jsonify({'recording': False})

@app.route('/api/camera/stream')
def camera_stream():
    """Stream camera feed as MJPEG using continuous still captures"""
    def generate_frames():
        """Generate MJPEG frames by capturing stills continuously"""
        import tempfile
        
        while True:
            try:
                # Create a temporary file for each frame
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp_path = tmp.name
                
                # Capture a single frame quickly
                cmd = [
                    'rpicam-still',
                    '-n',  # No preview
                    '-o', tmp_path,
                    '-t', '1',  # Minimal timeout
                    '--width', '640',
                    '--height', '480',
                    '--quality', '80'  # Lower quality for faster streaming
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=2
                )
                
                if result.returncode == 0 and os.path.exists(tmp_path):
                    # Read the image file
                    with open(tmp_path, 'rb') as f:
                        frame = f.read()
                    
                    # Clean up temp file
                    os.unlink(tmp_path)
                    
                    # Yield frame in MJPEG format
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                else:
                    # Clean up temp file on error
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"Stream error: {e}")
                if os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                time.sleep(0.1)
    
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/camera/media/<media_type>/<filename>')
def serve_media(media_type, filename):
    """Serve captured photos or videos"""
    try:
        if media_type == 'photos':
            filepath = os.path.join(PHOTOS_DIR, filename)
        elif media_type == 'videos':
            filepath = os.path.join(VIDEOS_DIR, filename)
        else:
            return jsonify({'error': 'Invalid media type'}), 400
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(filepath)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/media/list', methods=['GET'])
def list_media():
    """List all captured photos and videos"""
    try:
        photos = sorted(
            glob.glob(os.path.join(PHOTOS_DIR, '*.jpg')),
            key=os.path.getmtime,
            reverse=True
        )
        videos = sorted(
            glob.glob(os.path.join(VIDEOS_DIR, '*.h264')),
            key=os.path.getmtime,
            reverse=True
        )
        
        return jsonify({
            'success': True,
            'photos': [
                {
                    'filename': os.path.basename(p),
                    'url': f'/api/camera/media/photos/{os.path.basename(p)}',
                    'timestamp': os.path.getmtime(p),
                    'size': os.path.getsize(p)
                }
                for p in photos
            ],
            'videos': [
                {
                    'filename': os.path.basename(v),
                    'url': f'/api/camera/media/videos/{os.path.basename(v)}',
                    'timestamp': os.path.getmtime(v),
                    'size': os.path.getsize(v)
                }
                for v in videos
            ]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/camera/media/delete', methods=['POST'])
def delete_media():
    """Delete a photo or video"""
    try:
        data = request.get_json()
        media_type = data.get('type')
        filename = data.get('filename')
        
        if media_type == 'photo':
            filepath = os.path.join(PHOTOS_DIR, filename)
        elif media_type == 'video':
            filepath = os.path.join(VIDEOS_DIR, filename)
        else:
            return jsonify({'success': False, 'error': 'Invalid media type'}), 400
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'success': True, 'message': 'File deleted'})
        else:
            return jsonify({'success': False, 'error': 'File not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== SYSTEM MONITORING ENDPOINT =====

@app.route('/api/system/stats', methods=['GET'])
def get_system_stats():
    """Get Raspberry Pi system statistics"""
    try:
        import psutil
        
        # CPU Temperature (Raspberry Pi specific)
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                cpu_temp = float(f.read().strip()) / 1000.0
        except Exception as e:
            print(f"Warning: Could not read CPU temperature: {e}")
            cpu_temp = 0.0
        
        # CPU usage per core
        cpu_cores = psutil.cpu_percent(interval=0.1, percpu=True)
        
        # Memory info
        mem = psutil.virtual_memory()
        ram_total = round(mem.total / (1024**3), 1)
        ram_used = round(mem.used / (1024**3), 1)
        ram_percent = round(mem.percent, 1)
        
        # Swap info
        swap = psutil.swap_memory()
        swap_total = round(swap.total / (1024**3), 1)
        swap_used = round(swap.used / (1024**3), 1)
        swap_percent = round(swap.percent, 1)
        
        # Top processes by CPU
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent'] and pinfo['cpu_percent'] > 0:
                    processes.append({
                        'name': pinfo['name'][:20],  # Truncate long names
                        'cpu': round(pinfo['cpu_percent'], 1)
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage and get top 8
        top_processes = sorted(processes, key=lambda x: x['cpu'], reverse=True)[:8]
        
        print(f"System stats: temp={cpu_temp}°C, RAM={ram_used}/{ram_total}GB, processes={len(top_processes)}")
        
        return jsonify({
            'success': True,
            'cpu_temp': round(cpu_temp, 1),
            'cpu_cores': [round(c, 1) for c in cpu_cores],
            'ram_total': ram_total,
            'ram_used': ram_used,
            'ram_percent': ram_percent,
            'swap_total': swap_total,
            'swap_used': swap_used,
            'swap_percent': swap_percent,
            'top_processes': top_processes
        })
        
    except ImportError as e:
        print(f"ERROR: psutil not available: {e}")
        return jsonify({'success': False, 'error': f'psutil not installed: {str(e)}'}), 500
    except Exception as e:
        print(f"ERROR in get_system_stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Run on all interfaces so it can be accessed from other devices on the network
    app.run(host='0.0.0.0', port=5000, debug=True)
